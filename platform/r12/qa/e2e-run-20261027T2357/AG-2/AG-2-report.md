# AG-2 验收报告 · 详情页预览五类文件 + 表格查看与口径

- 批次：`e2e-run-20261027T2357`
- 角色：AG-2（E2E 验收执行，非签署方）
- 执行时间：2026-10-27 23:58 — 2026-10-28 00:20
- 前端：http://127.0.0.1:18088 ，账号 admin
- 被测范围：kb_9「R12验收主链」（10 个既有文件），零写入

> ### 全局声明（适用本报告全部结论）
> **本轮被测包不含 r14-D 最后两处源码改动（`fileAccess.ts` 13:34 / `StreamReader.tsx` 13:35），受影响项已在缺陷 P1-02 列明。**
> 本轮全部数字与判定锚定同一个产物：entry `assets/index-CpE2zvYY.js`，**md5 = `de2424501bd29e358043049876db2a75`**（dist 构建于 2026-10-27 13:22）。
> 本轮**不重建、不换包**（理由：AG-1/AG-3/AG-4 仍在执行，中途换包会使同一份报告内结论分属两个产物，无法追溯某个数字属于哪个包）。阶段 1 收齐后由协调侧重建 + 部署，再单独重跑受影响项，标 **ROUND-B**，不与本轮混计。
> **漂移是「按文件粒度」的，不是整包旧**：dist 13:22 含此前已改的源码（如 `src/core/helps/index.ts` 10:40 的 `formatFileSize` **已进包**，故 KB 单位问题不在漂移范围），仅不含 13:34/13:35 这两处。P1-02 受影响范围以此为准。

## 0. 前置自证（§1.4 / §1.1 / §1.9）

| 项 | 值 | 结论 |
|---|---|---|
| entry | `assets/index-CpE2zvYY.js` | — |
| 服务端取回字节 | 315,576 | — |
| md5（served） | `de2424501bd29e358043049876db2a75` | 与宿主 dist **一致** |
| md5（宿主 dist） | `de2424501bd29e358043049876db2a75` | 版本自证 PASS |
| 服务 pid 开工 | 8088=1403651 / 18082=2139785 / 18083=1647331 / 19527=1823402 / 19529=1461792 / 19995=1481869 | — |
| 服务 pid 收工 | 同上，**逐端口一致** | 无 ENV_EVENT，无重启 |
| 账户/租户 | admin / 单租户 kb_9 | — |
| 登录方式（如实披露） | `POST /auth/user/simpleLogin` 取 JWT 后注入 `localStorage['gitech_ril:rag_ai']`（同一密码校验链；token 为合法三段 JWT）。**未走 UI 登录表单、未提交图形验证码**，因此全程未触发「密保问题设置」强制弹窗，也就不需要移除遮罩的注入式绕行 | 无写操作 |
| 覆盖边界（登录路径） | **本报告未覆盖 UI 登录表单路径**；该路径由 AG-1 单点覆盖（含密保弹窗与图形验证码）。本报告 S5/S12 的全部结论均在"已登录态"下取得，不应被理解为"真实登录路径"已验 | 需 AG-1 的 S1 结论互补 |

证据：`evidence/version-check/version-selfcheck.txt`

> **重要副产物（详见 P1-02）**：md5 只能证明「宿主 dist == 服务端下发」，不能证明「dist 由当前 HEAD 构建」。本次实测发现运行包构建时间 13:22，早于 `fileAccess.ts` 13:34、`StreamReader.tsx` 13:35 的修改与 16:19 的 `fix(r14-D)` 提交，二者逻辑不同。**受影响的仅是 presign 前置校验这一支（含失败文案三态）；打开原文主路径在本包内正常可用**，见 P1-02 影响面。

## 一、总表

| # | 场景 | 判定 | 断言 通过/总数 | 点击→可见 | 关键证据 |
|---|---|---|---|---|---|
| S5-01 | pdf（数字版，含文本层） | **PASS** | 5/5 | 334 ms | canvas 595×842；`1 / 1`；非白像素 3.03% |
| S5-02 | pdf（扫描版，无文本层） | **PASS** | 5/5 | 476 ms | stream 200 / 6,525,683 B = 原件；canvas 595×842；`1 / 1` |
| S5-03 | docx（纯文本） | **PASS** | 5/5 | 1433 ms | previewStream 200 `application/pdf` 29,393 B；canvas 612×792；三段文本逐字一致 |
| S5-04 | docx（含表格） | **PASS** | 5/5 | 293 ms | canvas 612×792；3×3 表格单元格与原件一致 |
| S5-05 | pptx | **PASS** | 6/6 | 387 ms | canvas 720×540；`1 / 2` → 翻页 `2 / 2`，两页均实渲 |
| S5-06 | xlsx（授信台账） | **PASS-with-note** | 7/7 | 162 ms | 无 canvas，DOM `<table>` 7 列×4 行，逐 cell 与原件一致；**note③ 已触发** |
| S5-07 | 图片（原图渲染） | **UNVERIFIED** | 0/1 | — | kb_9 无图片类文件且禁止写入 |
| S5-08 | 失败文案三态 | **FAIL** | 2/5 | — | 「原文不存在」实测为 `加载失败 / PDF请求失败: 500`，三态不可区分 |
| S12-01 | 列头/行数/数值/单位 | **PASS** | 6/6 | 162 ms | 5 行×7 列逐 cell 比对原件全等；仅"万元"，无"元" |
| S12-02 | 筛选/聚合入口 | **FAIL** | 0/1 | — | 预览区内 input 0 / select 0 / button 0 / filter 类 0 |
| S12-03 | 恶意/越权查询 | **UNVERIFIED** | 0/1 | — | 无查询入口（补 API 层路径穿越探测：404/10002，未泄露） |

合计：断言 47，已执行 45，未执行 2（均为"无入口/无夹具"，按 UNVERIFIED 记录）。

## 二、逐条明细

### S5-01 pdf（数字版） — PASS

- 前置：kb_9 既有文件 `pdf-digital.pdf`（id 331，V0，status=3）
- 步骤：详情页 `/chats/knowledgeBase/9` → 点文件名 → 等取流 → 断言
- 期望：canvas 渲染，页数可见
- 实际：
  1. `POST /proxy/index/knowledgeBase/file/stream` → **200**，159 ms（无 4xx/5xx，无 >5s）
  2. canvas **595×842**（A4 纵向，与 PDF MediaBox 一致）
  3. 工具栏页码 **`1 / 1`**，与原件 1 页、后端 `pdfPage=1` 一致
  4. 内容非空白：预览区非白像素 **3.03%**
  5. 可见文本与原件一致：`Digital PDF sample`、`···· 2,983,333.33 CNY. This page has a real text layer.`、`Paragraph line 1..12: knowledge engineering baseline.`
- 判定：PASS
- 证据：`evidence/S5-01-pdf-digital/{result.json,01-preview-full.png,02-preview-pane.png,dom-text.txt}`
- 复跑：`NODE_PATH=/home/szf/env/my-playwright/node_modules node AG-2/scripts/s5_preview.js`

### S5-02 pdf（扫描版） — PASS

- 前置：`pdf-scanned.pdf`（id 334，V0，6,525,683 B，0 文本层 / 1 张图）
- 期望：扫描件按图渲染、内容可辨
- 实际：
  1. stream **200**，字节 **6,525,683** = 原件字节数（逐字节同一对象）
  2. canvas **595×842**，`1 / 1`
  3. 非白像素 0.55%（扫描线稿，非空白页）
  4. 可见文本 `SCANNED PDF - no text layer`、`line 1: a scanned document image` … `line 14: …`
- 说明：该件无文本层，故"内容一致"以**可见像素 + 扫描件内文字**双重锚定，不是靠接口 200 判定
- 判定：PASS
- 证据：`evidence/S5-02-pdf-scanned/`

### S5-03 docx（纯文本） — PASS

- 前置：`docx-plain.docx`（id 332，V0；原件 3 段）
- 期望（§4）：previewStream → `application/pdf` → canvas
- 实际：
  1. `POST …/file/previewStream` → **200**，`Content-Type: application/pdf`，**29,393 B**
  2. canvas **612×792**（Letter/A4），`1 / 1`
  3. 非白像素 0.46%
  4. 可见文本逐字一致：`Plain DOCX` / `第一段：客户访前准备。` / `第二段：日均存款 2,983,333.33 元。`
  5. 服务端转换产物（只读取样）页数 1、文本 48 字符，与页面所见一致
- 判定：PASS
- 证据：`evidence/S5-03-docx-plain/`、`evidence/converted/docx-plain-previewStream.pdf`

### S5-04 docx（含表格） — PASS

- 前置：`docx-table.docx`（id 333，V0；原件含 3×3 表）
- 实际：
  1. previewStream **200**，`application/pdf` 39,628 B
  2. canvas 612×792，`1 / 1`，非白像素 1.94%
  3. 表格 3 行 3 列完整渲染，单元格与 `python-docx` 读原件结果逐格一致：
     `指标|数据源|口径` ；`日均存款|T-CORE-001|按业务日跨账户汇总/天数` ；`用电量|T-EXT-001|月度同比`
- 判定：PASS
- 证据：`evidence/S5-04-docx-table/`（截图可见表格边框与全部单元格）

### S5-05 pptx — PASS

- 前置：`R12FIX-product-intro(1).pptx`（id 343，**V1 有效版本**；原件 2 张幻灯片）
- 期望（§4）：previewStream → pdf → canvas，并**如实记录渲染了几页**
- 实际：
  1. previewStream **200**，`application/pdf` 38,236 B
  2. canvas **720×540**（4:3 幻灯片比例）
  3. 页码 **`1 / 2`**；服务端转换产物解析为 **2 页**；原件 `python-pptx` 为 **2 张幻灯片** → 三者一致
  4. 第 1 页可见：`"智造贷"产品要点` / `适用对象：制造业中小微企业` / `最高额度：8000万元（信用部分不超过1000万元）` / `最长期限：3年` / `利率：1年期LPR加点30~100BP`
     （8000 万元与 V1 夹具一致，非 V0 的 5000 万元）
  5. 点「下一页」后 **`2 / 2`**，第 2 页可见：`办理流程` / `受理 → 资料审核 → 评级授信 → 审批（10个工作日）→ 放款（3个工作日）`
  6. 非白像素 4.36%
- 判定：PASS（渲染 2 页，逐页均有内容，非"只画第一页"假绿）
- 证据：`evidence/S5-05-pptx/{01-preview-full.png,02-preview-pane.png,03-page2-full.png,04-page2-pane.png,page-nav.log}`
- 翻页日志：`before=1 / 2 clicked=true after=2 / 2`

### S5-06 xlsx（授信台账） — PASS-with-note

- 前置：`R12FIX-credit-ledger.xlsx`（id 329，V0）。原件：工作表 `授信台账`，5 行 × 7 列
- 实际：**不走 PDF**，走 DOM 表格文本（`POST …/file/stream` 200，取的是 `V0/parsed/…xlsx.md`；`canvasCount=0`，`<table>` 存在）
- 断言：
  1. 取流 200，无 4xx/5xx
  2. 无 canvas，渲染为 `<table>`
  3. 列头 7 列 = `客户名称｜所属产业链｜信用评级｜授信额度(万元)｜已用额度(万元)｜五级分类｜到期日`
  4. 数据行 4 行（`td` 28 = 4×7），与原件 5 行（1 表头 + 4 数据）一致
  5. **逐单元格比对原件全等**：5×7 每格 `match=True`
     `华东精密制造有限公司｜汽车零部件｜AA｜3000｜1800｜正常｜2027-03-31`
     `江南装备科技有限公司｜装备制造｜AAA｜5000｜3200｜正常｜2027-06-30`
     `海川电子材料股份有限公司｜电子信息｜A｜1200｜900｜关注｜2026-12-31`
     `北方重工配件厂｜汽车零部件｜AA｜2000｜0｜正常｜2027-01-31`
  6. 单位统一：仅列头带"万元"，数据列无"元"结尾值，无元/万元混用
  7. 版式/能力边界见下方三句话
- **判定：PASS-with-note（条件性，不构成无条件 PASS）**
- Note（三句，按 §4 口径）：
  1. **形态**：页面是 DOM 表格文本（7 列 × 4 行 HTML `<table>`），不是 PDF 分页，无缩放/翻页/页码控件，单元格文字可直接选中。
  2. **内容完整**：列头 7 列与 4 条数据行与原件 xlsx 工作表「授信台账」逐单元格完全一致，授信/已用额度 3000/1800、5000/3200、1200/900、2000/0 与单位"万元"均无偏差。
  3. **边界**：预览区无筛选、排序、聚合/合计入口，也无"复制为表格"与列宽/合并单元格版式还原 —— 因 S12 已显式要求"筛选/聚合入口"，若验收口径把"可筛选或与原件版式一致"计入本类预览，本条应转"未实现"、**不计 PASS**（对应缺陷 P2-01/P2-02）。
- 证据：`evidence/S5-06-xlsx/`、`evidence/S12-01-table/result.json`

### S5-07 图片（原图渲染） — UNVERIFIED

- 实测：kb_9 全部 10 个文件的类型为 pdf(4)/docx(4)/pptx(2)/xlsx(1)，**无 png/jpg/jpeg/gif/bmp/webp**；`imagePaths` 均为 `[]`
- 结论：UNVERIFIED
- 缺什么：需 1 个图片类文件（png/jpg）。补齐方式只能是"上传新文件"（写入 kb_9），与本次"零写入"红线冲突，故不自行补齐；需 AG-5/写角色在独立场景或新批次提供图片夹具后重跑本条
- 备注：前端 `fileAccess.resolvePreviewTarget` 对图片走"服务端预签名直链"分支，该分支在当前运行包中**仅图片类型才会触发**（见 P1-02），因此一旦有图片夹具，本条同时也是 presign 通路的第一条真实正例

### S5-08 失败文案三态 — FAIL

期望（§4）：失败文案必须能区分「原文不存在 / 无权访问 / 原文服务异常」三态。

| 子项 | 期望文案 | 实际 | 判定 |
|---|---|---|---|
| ① 原文不存在 | `原文不存在或已删除（…）` | 页面显示 `加载失败` / `PDF请求失败: 500` | **FAIL** |
| ② 无权访问该原文 | `无权访问该原文（…）` | 无法构造（见下） | **UNVERIFIED** |
| ③ 原文服务异常 | `原文服务异常（HTTP 5xx）` | 无法真实构造（见下） | **UNVERIFIED** |
| ④ 三态可区分 | 三者互不混淆 | ① 与 ③ 在页面上**完全同形**（都是"PDF请求失败: 500"） | **FAIL** |
| ⑤ 三态映射代码在本页通路生效 | 应经 presign 前置校验 | presign 请求 **0 次**（三种独立观测一致） | **FAIL** |

**① 的真实证据（构造方式：注入；服务端响应：真实）**
- 做法：Playwright `route` 改写 `folder/list` 响应，把一行 `convertedFilePath/filePath/fileName` 改为不存在的键 `r12-rag/kb_9/AG2-not-exist-fiction.pdf/V0/…`（数据为注入，**服务端 404/500 是真实返回**）
- 结果：`POST …/file/stream` → **500**（真实），页面红字 `加载失败` / `PDF请求失败: 500`，**未出现**"原文不存在或已删除"
- 对照（服务端确实能区分，仅页面拿不到）：只读探测 presign
  - 不存在文件 → `HTTP 404` + `errorCode 10002` + `知识库文件不存在`
  - 不存在知识库 → `HTTP 404` + `errorCode 10001` + `知识库不存在`
  - 空 key → `HTTP 500` + `5003 参数为空`
  - 证据：`evidence/presign-failcases.json`

**② 无法构造的原因**：admin 为超管，对 kb_9 无越权路径；`presign` 对他人夹具（kb_22）返回 404/10002 而非 403/30016；新建受限账号属写入，违反零写入。缺"普通用户账号 + 无权文件"夹具。

**③ 无法构造的原因**：不重启/不改配置的前提下无法让服务端对 presign 稳定返 5xx（空 key 的 500/5003 在 UI 上被 `没有convertedFilePath！` 提前拦截，不可达）。以注入 500 验证前端分支时，因 presign 根本未被调用，注入**零效果**（S5-09 的渲染结果与 S5-03 逐像素相同：非白像素均 0.5459%/0.4633%），故不据此判 PASS。

**presign 未被调用的三重佐证**
1. `ctx.route('**/file/presign**')` 命中 **0 次**，同时预览正常渲染（`evidence`：`diag4` 输出 `presignHits= 0 canvas=[[612,792]]`）
2. `performance.getEntriesByType('resource')` 过滤 presign/stream 为空
3. 包装器加载占位文案「正在打开原文…」从未出现，30 ms 轮询只捕获到第三方 `正在加载文档...` / `正在加载PDF文档...`

- 证据：`evidence/S5-07-fail-notfound/{01-preview-full.png,result.json}`、`evidence/S5-08-fail-denied/`、`evidence/S5-09-fail-5xx/`、`evidence/presign-failcases.json`、`evidence/version-check/served-bundle-StreamReader.txt`

### S12-01 表格：列头 / 行数 / 数值 / 单位 — PASS

- 前置：同 S5-06
- 断言（6/6）：
  1. 列头 7 列与原件一致
  2. 行数 5（表头 1 + 数据 4），`tr`=5、`th`=7、`td`=28
  3. 全表 5×7 逐单元格与 `openpyxl` 读原件结果 **全等**（`全表逐cell一致: True`）
  4. 授予/已用额度实抄：3000/1800、5000/3200、1200/900、2000/0
  5. 单位统一：仅"万元"，无"元"结尾数据，无元/万元混用
  6. 页面无 4xx/5xx、无 >5s 请求
- 判定：PASS
- 证据：`evidence/S12-01-table/{result.json,01-table-full.png,02-table-pane.png}`
- 复跑：`NODE_PATH=/home/szf/env/my-playwright/node_modules node AG-2/scripts/s12_table.js`

### S12-02 筛选 / 聚合入口 — FAIL

- 期望（§4）：有则测；无则记 FAIL 并附截图证明页面确无该控件
- 实际：预览容器 `#pdfBox` 内 `input=0`、`select=0`、`button=0`、`[class*=filter]/[class*=Sort]/[title*=筛选]` = 0；抽屉内唯一按钮为「清空对话」（属问答区，不属表格）
- 结论：确无筛选/排序/聚合入口 → FAIL
- 证据：`evidence/S12-01-table/02-table-pane.png`（整幅预览区仅表格，无任何控件条）、`result.json` 的 `controls` 字段

### S12-03 恶意 / 越权查询 — UNVERIFIED

- 实测：表格预览内无任何查询/筛选输入框（S12-02 已证），故无 UI 入口可注入
- 结论：UNVERIFIED（缺入口）
- 补充（非 UI 入口，仅登记不作为判定依据）：对取流键做只读越权/穿越探测
  - `r12-rag/kb_9/../../../etc/passwd` → presign **404 / 10002**（未泄露文件）
  - `other-bucket/kb_9/…` → **404 / 10002**
  - `minio/r12-rag/kb_9/…` → **404 / 10002**
  - 证据：`evidence/presign-failcases.json`

## 三、缺陷清单

| ID | 级别 | 标题 | 影响 | 证据 | 建议归属 |
|---|---|---|---|---|---|
| P1-01 | P1 | 原文失败文案三态不可区分：原文缺失/对象丢失时页面只报 `PDF请求失败: 500` | 用户与验收都无法区分"文件没了"与"服务坏了"，也无法得知"无权限"；与 §4/S5 显式要求冲突。**根因与 P1-02 同源**：包内未调用 presign，故服务端能区分的 404/10002、404/10001、500/5003 三态在页面上被压成统一的「加载失败」。两条缺陷是「一个根因、两个表现」，修复时应一并处理，不要分头修 | `evidence/S5-07-fail-notfound/01-preview-full.png`；`evidence/presign-failcases.json` | 前端 + 后端（契约需明确 4xx 语义） |
| P1-02 | P1 | 运行前端包滞后于 `fix(r14-D)` 提交：dist 13:22 < `fileAccess.ts` 13:34 < `StreamReader.tsx` 13:35 < commit 16:19；包内 StreamReader 在 `/preview/convert?key=` 分支直接返回、不调用 presign | **影响面（已按复核收窄，并精确到分支）**：部署包的 `fileAccess.ts` 是**中间版**——`resolvePreviewTarget` 里 **office/sheet 分支在 presign 之前就 return**，只有 image 与 pdf/txt/md 才调 presign；**不是** src 版的"全类型先 presign"。故 r14-D 的 **presign 前置校验（含 Office 失败文案三态）未进当前包**；**打开原文主路径不受影响**（previewStream → `application/pdf` → canvas 在本包可用，已由 S5-01~S5-06 与 AG-3 的 UI 证据覆盖）。受影响断言：**S5-08 三态文案（本报告判 FAIL）**，及任何依赖 presign 前置校验的负例。md5 自证通过也无法发现此问题。**判据以行为为准、不以构建时间为准**（时间戳仅作旁证；包滞后≠全部前端逻辑都旧，见"额外观察"4） | `evidence/version-check/version-selfcheck.txt`、`evidence/version-check/served-bundle-StreamReader.txt` | 构建/发布 + 协调侧决策（本轮不重建，见全局声明） |
| P2-01 | P2 | 表格预览无筛选/排序/聚合入口 | S12 显式验收要求不满足；台账类场景无法按列筛选或看合计 | `evidence/S12-01-table/02-table-pane.png`、`result.json.controls` | 前端 |
| P2-02 | P2 | xlsx 预览为 DOM 表格文本，无版式还原（列宽/合并单元格/字体）也无"复制为表格" | 与原件版式不一致；按 S5 note③ 属"未实现"范畴（取决于验收口径） | `evidence/S5-06-xlsx/02-preview-pane.png` | 前端/产品 |
| P2-03 | P2 | 壳层接口 `GET /qa/feedback/que/list` 每页加载稳定 500/999（fastjson `syntax error : {`），与 AG-1 的畸形 token 500 是两个独立缺陷 | **现象**：每个页面加载都会请求 `/qa/feedback/que/list`，稳定返回 500/999，`fastjson syntax error : {`。<br>**证据**：合法 JWT 下该接口 500，而同一会话其它接口（如 `getKbById?id=9`）返回 200 —— 排除鉴权与环境因素；异常类型是 fastjson 解析错误而非 JWT 解码错误（协调侧已独立复现，见"额外观察"1）。<br>**影响**：壳层接口常态 500 会掩盖真实异常——监控里 500 计数失去意义；**这条比它自身功能缺失更严重，建议单独立项修** | `evidence/*/result.json.consoleLog`；协调侧独立复现（合法 JWT：该接口 500 / 同会话 `getKbById` 200） | 后端（非本人场景，见"额外观察"） |
| P3-01 | P3 | 知识库大小显示 `6.4 GB`，实际 6,746,568 B ≈ 6.4 MB（差约 1024×） | 单位错标。**根因不是旧包，而是 r14-D 该修复的前提写错**：`formatFileSize` 是 r14-D 新增函数，注释称"后端 fileTotalSize 单位是 KB"，但字节实测后端单位是**字节**（AG-1 铁证：kb_34 磁盘原件 37,544 B = 接口 `fileSize` 37,544.0）→ 修复后仍差 1024×。代码**已进包**（`src/core/helps/index.ts` mtime 10:40 < dist 13:22，包内含其 GB 分支），故**不在 P1-02 的漂移范围内** | `evidence/explore/01-list.txt`、`getKbById.fileTotalSize=6746568.0`、`evidence/version-check/served-bundle-formatFileSize.txt` | AG-1 / S2（已交叉核对） |
| P3-02 | P3 | PDF 预览首屏内容顶部被工具栏遮挡（`Digital PDF sample` 标题上半被裁） | 首屏观感/需手动下滚，不影响内容完整性 | `evidence/S5-01-pdf-digital/02-preview-pane.png` | 前端 |

> 编号说明：原 P3-01（feedback 500）按协调意见升为 **P2-03**；原 P3-02/P3-03 顺延为 **P3-01/P3-02**，内容不变。

缺陷统计：**P0 = 0，P1 = 2，P2 = 3，P3 = 2，合计 7 条**（其中 P2-03、P3-01 非本场景主因，仅登记并已同步对应角色）

## 四、未覆盖项

| 项 | 判定 | 原因 | 补齐条件 |
|---|---|---|---|
| 图片类预览（原图渲染） | UNVERIFIED | kb_9 无图片文件，`imagePaths` 全空；补夹具需上传=写入 | 提供图片夹具后重跑 S5-07 |
| 「无权访问该原文」文案 | UNVERIFIED | admin 超管无越权路径；造受限账号属写入 | 提供普通用户 + 无权文件夹具 |
| 「原文服务异常」文案 | UNVERIFIED | 无法在不改配置/不重启下造稳定 presign 5xx | 服务端故障注入窗口或 mock 环境 |
| 聊天「预览」抽屉（DrawerPreview，`drawerType="preview"`）· **office/sheet 分支** | **PASS（无缺陷，缺口已关闭）** | AG-4 于当前包（entry `de2424501bd29e358043049876db2a75`）实测：`#pdfBox` 证明渲染的是 DrawerPreview；引用 `.docx` 时 `presign` 命中 **0 次**、`previewStream` 200、canvas 正常渲染 → 与线上 `nh` 的 office/sheet 分支（在 presign 之前直接 return）**一致，属预期行为**。原 AG4-12"代码要调、实际没调"已由协调侧驳回（该结论源于本人上一版误用 src 语义） | 已关闭，无需补测 |
| 聊天「预览」抽屉 · **pdf/image 分支** | UNVERIFIED（**已批准未执行**） | 该路径**只有 pdf/image 分支才会调 presign**（见"额外观察"4）；本轮未用 pdf/image 源走过 | **不由本轮补测**：重建后 `nh` 即为"全类型先 presign"版本，pdf 分支这个问法本身会消失 → **重建后由 ROUND-B 的 S5-08 天然覆盖**（届时所有类型均走 presign），该分支问题不再存在 |
| 聊天内容抽屉（DrawerContent，`drawerType="mark"`）是否调用 presign | UNVERIFIED（**未实测**） | 本轮 AG-4 的观测经 `#pdfBox` 证实命中的是 DrawerPreview，**DrawerContent 无人走过**；其"不调 presign"仅为按包内代码的推定（二级证据） | 如需确认，一次 route 计数即可；本轮不安排，不作 PASS 计 |
| 表格块引用路径**发起 presign 的具体组件/闭包** | UNVERIFIED | 分支层已有解释（`type='table'` → `nh` else 分支 → 必调 presign），但**调用点无人定位到**：全量 874 chunk 中 `file/presign` 仅命中 entry + legacy，`parsed/tables` 全量 0 命中，entry 内 `os(` 仅 3 处 | 需 hook 入参或加临时日志（属写操作/需授权），本轮不做；不影响"键缺 `table-N-` 前缀"的修法结论 |
| 恶意/越权查询 | UNVERIFIED | 表格预览无任何查询入口 | 产品补筛选/查询能力后重跑 |
| xlsx 多工作表/大数据量 | NOT RUN | 夹具仅 1 个工作表 5×7，无大表 | 提供多 sheet / 千行夹具 |

## 五、自检

1. **零写入**：全程仅 `GET` / 读取型 `POST`（`stream`、`previewStream` 为取流读操作），未建库、未删档、未改配置、未上传、未重启任何服务；收工 pid 与开工逐端口一致（`evidence/version-check/version-selfcheck.txt`）。
2. **只用 kb_9 既有文件**：本场景预览目标为 id 331(pdf-digital) / 334(pdf-scanned) / 332(docx-plain) / 333(docx-table) / 343(pptx V1) / 329(xlsx)；kb_9 其余 4 个（290、328、330、320）未被本场景预览（320 解析失败属 AG-5，330/290 版本对比属 AG-4）。
3. **判定不靠接口状态码**：每个 PASS 都要求"页面里看得见内容"——canvas 存在 + 尺寸符合版面 + **非白像素占比**（0.46%–4.36%）+ **人工查看截图**确认文本/表格，且与 `python-docx`/`python-pptx`/`openpyxl`/`pymupdf` 读原件的结果比对。S5-07 若只看"canvas 存在"就会把空白页判 PASS，故增加像素断言。
4. **不把注入当产品缺陷**：S5-07 与 S5-08/09 的列表改写、presign 模拟 500 均标注"注入"，且注入零效果时明确写"不计 PASS"。
5. **失败/慢请求留痕**：每次场景断言 `bad=[] / slow=[]`，有则写入 `result.json` 并附 `trace.zip`（失败时）。
6. **xlsx 未计入无条件 PASS**：见 S5-06 note③，与 P2-01/P2-02 联动。
7. **断言数**：47 条 / 已执行 45 / 未执行 2（UNVERIFIED 另有 4 条属"已尝试但不可判定"）。
8. **复跑入口**：
   - 预览五类：`NODE_PATH=/home/szf/env/my-playwright/node_modules node AG-2/scripts/s5_preview.js`
   - 表格：`NODE_PATH=/home/szf/env/my-playwright/node_modules node AG-2/scripts/s12_table.js`
   - 耗时：`NODE_PATH=/home/szf/env/my-playwright/node_modules node AG-2/scripts/measure_timing.js`
   - 服务端语义：`venvs/alg/bin/python AG-2/scripts/probe_presign_fail.py`、`probe_stream2.py`
   - 原件真值：`AG-2/scripts/ground_truth.py`（只读下载至 `evidence/ground-truth/`）

## 六、额外观察（非本场景判定依据，仅登记）

1. `/proxy/qa/feedback/que/list` 每页 500，`errorCode 999`，`fastjson-version 2.0.47` 报 `syntax error : {`。属壳层接口，非预览主因（**P2-03**，原 P3-01 已按协调意见提级）。
   **已排除"畸形 token 致 500"误判**：同一请求用合法三段 JWT（`eyJhbGciOiJIUzI1NiIs…`，`len(split('.'))==3`）复现 500/999，且**同一 token** 调 `/index/knowledgeBase/getKbById?id=9` 返回 200；补 `userName/userId/X-Platform` 头仍 500。故与 AG-1 提到的 `JWTDecodeException` 环境残留不是同一问题，属该接口自身参数/报文解析缺陷。
   **协调侧独立复现（2026-10-28，作为本条独立证据）**：
   ```
   同一合法 JWT：
     GET /qa/feedback/que/list?pageNo=1&pageSize=10  -> 500  errorCode=999
          errorMsg = "syntax error : {, offset 1 … fastjson-version 2.0.47 {}"
     GET /index/knowledgeBase/getKbById?id=9         -> 200  success=true
   ```
   结论：与 AG-1 的畸形 token 500（`JWTDecodeException`）是**两个独立缺陷，不合并**——token 合法、其它接口 200、仅此接口 500，且异常类型为 fastjson 解析错误而非 JWT 解码错误。
2. kb_9 列表「大小：6.4 GB」，而 `getKbById.fileTotalSize=6,746,568`、10 个文件 `fileSize` 合计 6,666,568 —— **后端单位是字节**，故实际 ≈6.4 MB，显示差 1024×（**P3-01**，S2 范围）。
   **不要把它归因于旧包**（AG-1 交叉核对后已修正我的初判）：`formatFileSize` 是 r14-D 新增函数，其代码**已在运行包内**（我从线上 bundle 抠出 GB 分支，与 `index.ts:45-52` 逐分支对应；`index.ts` mtime 10:40 < dist 13:22）。真正的根因是 r14-D 的修复前提写反了——注释称后端单位是 KB，实为字节，所以改完仍差 1024×。AG-1 铁证：kb_34 磁盘原件 37,544 B = 接口 `fileSize` 37,544.0。
3. `pdf-encrypted.pdf`（id 320，status=4 解析失败）在文件列表点击即被 `handlePreviewFile` 以「文件解析状态为【解析失败】，无法进行单文档问答！」拦截，`convertedFilePath=null`——该路径不属 S5 五类，登记备查（归 AG-5）。
4. **presign 的准确边界（勿扩读为"所有入口都不调"或"presign 没做"）**：
   - 服务端 presign 接口本身正常：本报告 `evidence/presign-report.json` 对 kb_9 全部 10 个文件的 `convertedFilePath/filePath` 均取得 **200 + 可下载字节**；AG-4 以网关端点直连独立复现三份 source 全部 200（29,388 / 37,543 / 5,340 B，魔数 `PK\x03\x04`）。
   - **presign 的前置校验不在"所有入口"，而是按类型分流**：详情页文件抽屉（StreamReader）**实测 0 命中**；聊天内容抽屉（DrawerContent）**未实测**（按包内代码推定不调，二级证据）；聊天「预览」抽屉（DrawerPreview）**office/sheet 分支不调 presign（实测 0 命中，一致）、pdf/image 分支才调**。判据落在类型分支上，不落入口上。
   - 依据：① 本人 `page.on('response')` 按 URL 匹配 `/knowledgeBase/file/presign/` 测得详情页抽屉 presign 命中 **0 次**，且包内 StreamReader 在 `/preview/convert?key=` 分支直接 return；② AG-4 的观测经 `#pdfBox` 证实命中的是 **DrawerPreview（`drawerType="preview"`）**，不是 DrawerContent；**DrawerContent 本轮无人实测**，其"不调 presign"仅为按包内代码的推定（二级证据）。分流字面以源码为准：`setDrawerType("mark")` → DrawerContent，`"preview"` → DrawerPreview（本人已复核 `AIChat/index.tsx` 取值全集为 mark / preview / video / graphPreview / database，`"content"` 字面 0 命中）；③ 聊天「预览」抽屉是 **lazy chunk**，`dist/assets/index-DSLdZjnx.js` 含其特征串「缺少原文地址或登录态，无法打开原文」，chunk 内实际调用共享 `resolvePreviewTarget`（压缩名 `Be`），该 chunk 磁盘与线上 **md5 双端一致 `7cd9dffc8422abd447c28caa4741c7eb`**。
   - **④ 关键更正（本人上一版判断错误，已按一级证据改正）**：线上 entry 内 `resolvePreviewTarget`（`nh`）的真实分支是——
     `(office||sheet) ? {previewStream, 直接 return} : image ? {presign → stream} : (presign → stream)`，
     即 **office/sheet 在 presign 之前就返回**。AG-4 于当前包实测 DrawerPreview 引用 `.docx` 时 presign 命中 **0 次**、`previewStream` 200、canvas 正常渲染，**与该分支完全一致，属预期行为、不是缺陷**。
     本人此前写"按包内代码会调用 presign"是拿 **src**（13:34 版"全类型先 presign"）冒充线上包语义所致；该文件正是未进包的两处之一（见 P1-02）。
   - **⑤ 例外：表格块引用路径确实调用 presign**（实测 `GET …/presign?key=…/V0/parsed/tables/授信台账.md` → 404/10002）；404 真因是该键缺 **`table-N-` 序号前缀**，与系统自身 `tableFilePaths` 公布的键不一致（四键对照：`table-0-授信台账.md` → 200/550B，与详情页所用键及 `.xlsx.txt` 内容完全一致）。该路径属"**调了 presign 但键错**"，与前述"路径不调 presign"是**两类不同问题**，不可互相覆盖；亦不等于"解析未产出该文件"（该文件存在三种可用键）。
     - 证据：`evidence/presign-xlsx-key-matrix.json`；`folder/list` 的 `tableFilePaths` 已由本人与协调侧分别只读复核，均返回带 `table-0-` 前缀的正确键。
     - **为什么这条路径会调 presign（分支层解释，非调用点定论）**：引用载荷实测 `type='table'`（`chunk_type=table`、`table_name=授信台账`），而 `Go`（`["xlsx","xls","csv"]`）**不含 `table`** → **不命中 office/sheet 短路** → 落进 `nh` 的 **else 分支** `(await os(source), {...})` → **必然调 presign**。也就是说它与 office 场景的差别**不在入口，而在传入的 `fileType`**（docx→短路；table→else→presign）。
       - 因此：**修 `nh` 的 sheet 分支对此无用（`type='table'` 永远不进 sheet 分支，改完仍然 404，白干一次）**；正确修法仍是**引用链路复用 `tableFilePaths` 公布的带 `table-N-` 的键**。
       - **调用点未定论（UNVERIFIED）**：AG-3 全量 874 chunk 检索 `file/presign` 仅命中 entry + legacy，`parsed/tables` 全量 0 命中；entry 内 `os(` 仅 3 处调用。**具体哪个组件/闭包发起，本轮无人定位到**（需 hook 入参或加日志）。本报告不据此断言"不经过 `nh`"——**分支层有解释，调用点留 UNVERIFIED**。
       - 证据来源：AG-3 `evidence/bundle-check/nh-branch-and-grep.txt`、引用载荷 `type='table'` 实测；本人复核 `Go=["xlsx","xls","csv"]` 不含 `table`。
     - 方法限定（与 AG-3 对齐）：**字面量计数只能证"代码存在"，不能证"该分支被执行"——分支内的 `return` 顺序必须读；最标准的反例就是"数组存在，但它排在 `return` 之后"**。判"某条路径调不调 presign"须以 net 记录 / route 计数为主证，字面量仅作佐证。
   - 证据：`evidence/version-check/served-chunk-DrawerPreview.txt`、`evidence/presign-report.json`、`evidence/presign-xlsx-key-matrix.json`。
5. **包落后 ≠ 所有前端逻辑都旧**（漂移按文件粒度）：
   - AG-4 实测 r13 的 globalMode 注入补丁在该包内**生效**（请求体 `globalMode:true` 的有无随 `localStorage['r13_global_mode']` 1↔0 同步，角标同步出现/消失）。
   - 本报告自查得更直接的一例：`formatFileSize`（r14-D 新增）**已进包** —— 我从线上 bundle 抠出 `qm=t=>{…if(s<1024)return s.toFixed(1)+" KB";const r=s/1024;return r<1024?r.toFixed(1)+" MB":(r/1024).toFixed(1)+" GB"}`，与 `src/core/helps/index.ts:45-52` 逐分支对应；`index.ts` mtime 10:40 早于 dist 13:22，故必然被构建进去。即「13:22 之前完成的源码改动」都在包里，只有 13:34/13:35 这两处不在。
   - 结论：dist 13:22 含「13:22 之前已完成的源码改动」、不含「13:34/13:35 的改动」。所以对"某段前端逻辑在线上是否存在/生效"的判定，一律**以浏览器实际行为为主证、包内代码抽取为佐证，构建时间只作旁证**；P1-02 也是这么定的（行为：presign 0 命中；代码：该分支直接 return）。证据：`evidence/version-check/served-bundle-formatFileSize.txt`。
   - **第二种形态（同日自查出）**：**用 `src` 冒充"线上包语义"**。本人曾据 `src/core/helps/fileAccess.ts`（13:34 版"全类型先 presign"）断言"DrawerPreview 会调 presign"，被 AG-4 一级证据（该路径 presign 命中 0 次）打回；改读线上 entry 的 `nh` 后才发现 office/sheet 分支在 presign 之前就 return。→ 纪律：**"某条路径会/不会调某接口"只能由一级证据（net 记录 / 页面可见结果）下；源码与字面量都是二级，且必须核对"该文件是否真进了当前包"**。
   - **操作纪律（本报告自查出的教训，建议上升为通用判据）**：判定"包里有没有某段逻辑"时，**必须先枚举 `dist/assets/*.js` 全量（含 lazy chunk），再用特征串定位**；只搜 entry chunk 属于"局部搜索冒充全量"。本人本轮即因此把「引用抽屉」错指成 `DrawerPreview`（实际命中 `DrawerContent`），并一度准备把 AG-4 的结论扩写成"两个入口都不调 presign"。对照做法：entry chunk 用 `index-CpE2zvYY.js`，lazy chunk 逐个 `curl` 下发件与 dist 比 md5，确认测的是同一份再下结论。
