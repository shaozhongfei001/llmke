# -*- coding: utf-8 -*-
import io

p = 'AG-4-report.md'
s = io.open(p, encoding='utf-8').read()

# ---------- 1) §2.6 整体重写（最终版：归因=DrawerPreview；结论=与运行包一致，撤回 AG4-12） ----------
start = s.index(u'### 2.6 ')
end = s.index(u'### 2.7 ')

new_26 = u'''### 2.6 引用"展开原文"路径实测（ROUND-A 补充观测：抽屉身份已定死；结论是"与运行包一致"，不是缺陷）

> **本节有两处更正记录，都保留以便追溯：**
> ① 上一版把路径归因为 Content 抽屉 → **错**，实测是 **DrawerPreview**（证据见 (a)）。
> ② 上一版据此记了 AG4-12 "代码要调、实际没调"（P1）→ **该条已撤回**，因为"代码"要以**运行包**为准，
>    而运行包里的 `resolvePreviewTarget` 是**旧实现（不含 presign）**，见 (c)。撤回理由与时间证据在 (d)。

#### (a) 实测结果 + 抽屉身份（三条互不依赖的证据）

操作链：local 模式（global 关）提问「智造贷最高额度是多少？」→ 点「知识溯源 1」→ 点条目「R12FIX-product-loan.docx」。

| 证据 | 结果 |
|---|---|
| ① 触发事件（页面 console 采集） | **`knowledge_referenceFile_title:click`**；源码该分支 `AIChat/index.tsx:342-367` → `setCurFileInfo(d3)` + **`setDrawerType("preview")`** |
| ② 组件独有 DOM 标识 | 抽屉内 **`#pdfBox` 存在 = true**（`DrawerPreview.tsx:112` 独有；DrawerContent 不含该 id） |
| ③ 占位文案 | 「正在打开原文…」（`DrawerPreview.tsx:106`，target 未就绪才出现）**100ms × 12 次采样全部 false** |

三条独立证据一致 → **进入的是 `preview` 抽屉（DrawerPreview）**，不是 mark/Content 抽屉。

#### (b) 计数结果（仪器先自检，排除"测不到"）

| 观测项 | 结果 |
|---|---|
| 仪器自检：主动发一次真实 presign | `status=200`、`hasUrl=true`、**route 计数 +1** |
| 点击后的 `/file/presign` 命中 | **0 次**（URL 列表为空） |
| 实际取流请求 | `POST /proxy/index/knowledgeBase/file/previewStream` → **200** |
| 渲染 | 抽屉打开、`canvas=1`、标题 `R12FIX-product-loan.docx 1/1 111%`、正文可见（`RA-20-preview-drawer.png`） |
| 失败三态文案 | 0 次命中（走成功路径，未触发） |

> **口径撤回**：`performance.getEntriesByType('resource')` 在 Playwright route 拦截下**不记录**被拦截请求（自检时真实 presign 调用也只有 0 条 resource entry）。
> 故 performance 只能证"有"、不能证"无"，本报告只以 **route 计数**为准。

#### (c) 代码级证据：运行包里的 `resolvePreviewTarget` 不含 presign（这是 hits=0 的真正原因）

**源码（当前 HEAD 工作树）确实要求对所有类型先 presign** —— `core/helps/fileAccess.ts:85-109`：

```ts
export const resolvePreviewTarget = async ({ source, fileType, token }) => {
  const key = getObjectKeyFromSource(source);
  if (!key) throw new Error("缺少原文对象键，无法打开原文");
  // R14-D-FIX-04：**所有类型**先做一次 presign 前置校验。
  const presigned = await getPresignedObjectUrl(source, token);   // ← 无条件，先于任何 fileType 分支
  if (isImageType(fileType)) return { filePath: presigned, streamApiUrl: STREAM_API };
  if (isOfficePreviewType(fileType) || isSheetType(fileType))
    return { filePath: key, streamApiUrl: PREVIEW_STREAM_API };   // ← docx 走这里，但 presign 已发生过
  return { filePath: key, streamApiUrl: STREAM_API };
};
```

即：**不是"按 fileType 跳过 presign"**，docx 也会先 presign（TL 问的 (a)/(b) 两分支里，源码是 (a)：无分支、必走）。

**但"源码要求"≠"运行包要求"。时间证据：**

| 对象 | mtime | 说明 |
|---|---|---|
| `src/core/helps/fileAccess.ts`（含上面这段 presign 前置） | **2026-10-27 13:34:50** | 来自 commit `4415ed3`（16:19 `fix(r14-D): 引用打开原文 + 失败文案三态 + KB 大小单位`） |
| `dist/assets/index-CpE2zvYY.js`（entry） | **2026-10-27 13:22:11** | 构建产物 |
| `dist/assets/index-DSLdZjnx.js`（DrawerPreview 所在 lazy chunk） | **2026-10-27 13:22:11** | 同上 |

**源码比构建产物晚 12 分 39 秒** → presign 前置逻辑**不可能在运行包里**。
包内 grep 也一致：`index-CpE2zvYY.js` 中 `file/presign` 字面 ×1（`PRESIGN_API` 常量所在），
`index-DSLdZjnx.js` 中 `file/presign` ×0、`previewStream` ×0（该 chunk 通过 import 使用 entry 里的实现）。

#### (d) 最终判定（并撤回 AG4-12）

| 层 | 事实 | 判定 |
|---|---|---|
| 行为 | DrawerPreview 渲染成功，**presign 0 次**，改走 `previewStream` 200 | **已验** |
| 运行包代码 | 包内 `resolvePreviewTarget` 为**旧实现（无 presign）**，与"0 命中"完全自洽 | **行为与包一致 → 不是缺陷** |
| 源码 | 已改为"所有类型先 presign"，但**晚于构建，未进包** | **属版本漂移 / 未进包**，与 AG-2 的 P1-02「presign 前置校验一支未进包」**同源**，由该条覆盖，本报告不另立缺陷 |
| 失败三态文案 | 该路径不发 presign → 文案**未触发**；三态代码存在于包内，属"未触发"而非"未实现" | **UNVERIFIED** |

**因此：AG4-12 已撤回**（理由："代码要调"这句话当时比对的是 **src**，不是 **运行包**；运行包内本来就不调，
不存在"代码与行为矛盾"）。这条撤回本身是一条有价值的证据：**它把 AG-2 的"未进包"结论从"代码推断"抬成了"行为 + 时间戳双向印证"**。

证据：`RA-final.json`、`RA-identify.json`、`RA-result.json`、`RA-20-preview-drawer.png`、`RA-e3-panel-item.png`、`S8-ref3-result.json`。

'''
s = s[:start] + new_26 + s[end:]

# ---------- 2) 删除 AG4-12 行 ----------
lines = s.split(u'\n')
lines = [ln for ln in lines if not ln.startswith(u'| AG4-12 |')]
s = u'\n'.join(lines)

# ---------- 3) 计数回 11 条：P0 2 / P1 2 / P2 3 / P3 4 ----------
s = s.replace(u'缺陷 **12 条（P0 1=AG4-11 / P1 4 / P2 3 / P3 4）**',
              u'缺陷 **11 条（P0 2=AG4-01·AG4-11 / P1 2 / P2 3 / P3 4）**')
s = s.replace(u'## 3. 缺陷清单（12 条：P0 1 / P1 4 / P2 3 / P3 4）',
              u'## 3. 缺陷清单（11 条：P0 2 / P1 2 / P2 3 / P3 4）')

# ---------- 4) AG4-01 行 P1 -> P0 ----------
s = s.replace(u'| AG4-01 | P1（TL 最终定级：`/question` 给错数值，用户主路径不直接调用；权重低于 AG4-11） |',
              u'| AG4-01 | **P0**（TL 最终定级：错误数值被当作"成功答案"交付；判据=用户无法察觉地拿到错答案） |')

# ---------- 5) §3 "P0/P1 权重"块 -> P0×2 最终版 ----------
old_block_start = s.index(u'**AG4-11 = P0、AG4-01 = P1 的权重基准')
old_block_end = s.index(u'**两条仍必须分开记录（不合并）', old_block_start)
old_block_end = s.index(u'\n', s.index(u'**', s.index(u'合并成一条会让后者被当成前者的表现而被漏修。**', old_block_end) + 40))

new_block = u'''**两条都是 P0，但必须分开计数（TL 最终定稿，本报告采纳）**

```
AG4-01 = P0   错误数值当作"成功答案"交付（status=2、单帧、无错误终态）
AG4-11 = P0   UI 假开关（question_re 未实现 global）+ 失败前泄漏旧值
```

**定级理由（TL 原话口径）：保守优先 —— 两条各自满足一个 P0 判据，且修法不重叠；
宁可多阻断一条，也不要因为"用户主路径不经过"而把一条数据错误降级。
降级的代价是它被排到下一轮，而它不会自己消失。**

**两条仍必须分开记录（不合并）：独立机制、修法完全不同 —— AG4-01 改事实选择 / 摘要代次；
AG4-11 要在 `question_re` 里实现 global 或把开关在该端点下线。
合并成一条会让后者被当成前者的表现而被漏修。**
'''
s = s[:old_block_start] + new_block + s[old_block_end + 1:]

# ---------- 6) §2.8 定级段 -> P0×2 ----------
old_28 = u'''  - **AG4-11 = P0**：UI 的 global 是假开关（`question_re` 未实现 global），且失败前泄漏旧值；判据=用户在日常路径上会踩到（§2.7 R1 / §2.9）；
  - **AG4-01 = P1**：`/question` 给错数值（status=2、单帧、无错误终态）；判据=只有直接集成该端点的人会踩。
- 权重基准：**P0 给"用户日常路径会踩到的"，不是"理论上最坏"**。两者**独立机制、分开记录、不合并**（理由见 §3 块：修法完全不同，合并会让后者被当成前者的表现而漏修）。'''
new_28 = u'''  - **AG4-01 = P0**：错误数值当作"成功答案"交付（status=2、单帧、无错误终态）；
  - **AG4-11 = P0**：UI 假开关（`question_re` 未实现 global）+ 失败前泄漏旧值（§2.7 R1 / §2.9）。
- 定级口径：**保守优先** —— 两条各自满足一个 P0 判据、修法不重叠；宁可多阻断一条，也不因"用户主路径不经过"而降级（降级＝排到下一轮，而问题不会自己消失）。两者**独立机制、分开记录、不合并**（理由见 §3 块）。'''
assert old_28 in s
s = s.replace(old_28, new_28)

# ---------- 7) §0.2 里的 ROUND-A 句子 ----------
old_02 = s[s.index(u'  - **S8「点击引用打开原文」**（ROUND-A 补充观测后已重判'):]
old_02 = old_02[:old_02.index(u'\n')]
new_02 = (u'  - **S8「点击引用打开原文」**（ROUND-A 补充观测已完成，§2.6）：**渲染=可验 PASS**（能打开、能渲染）；'
          u'抽屉身份已定死为 **DrawerPreview**（`#pdfBox`）；**presign 0 次命中且与运行包一致**——'
          u'`fileAccess.ts` 的 presign 前置 mtime 13:34:50 **晚于** dist 构建 13:22:11，**未进包**，'
          u'故不记缺陷（与 AG-2 P1-02「未进包」同源）；失败三态文案 UNVERIFIED（未触发）。')
s = s.replace(old_02, new_02)

io.open(p, 'w', encoding='utf-8').write(s)
print('report rewritten')
