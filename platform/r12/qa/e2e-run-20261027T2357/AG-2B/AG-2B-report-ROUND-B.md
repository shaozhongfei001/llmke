# AG-2B · ROUND-B 报告（前端重建部署后复验）

编制：AG-2B（E2E 验收角色，非 QA 签署方）
编制时间：2026-10-28 11:11 ~ 11:30（本机时间）
范围：**严格按派工三项**（① 包内证据 ② S5-08 失败文案三态 ③ S5-07 图片预览），另附 1 条超范围但阻断级的额外发现。

---

## 0. 本轮锚点（所有结论都锚定这个包）

| 项 | 值 |
|---|---|
| entry asset | `assets/index-fup9RT0c.js` |
| **新包 md5** | **`5161c957f19bb7f1ee825ca33d6771cc`** |
| 大小 | 315,489 B（旧包 315,576 B） |
| dist mtime | 2026-10-28 11:11:00（旧包 2026-10-27 13:22） |
| 线上取回 md5 | `5161c957f19bb7f1ee825ca33d6771cc`（**dist == served，非 SPA fallback**） |
| 旧包 md5（ROUND-A） | `de2424501bd29e358043049876db2a75` |
| 等待过程 | 11:10:57 仍为旧包 → 11:11:17 检测到新包生效（轮询 20s/次，第 2 次命中） |
| 复核时刻 | 11:25:34 再次比对，md5 未漂移 |

证据：`evidence/00-build-anchor.txt`（含 HTTP 响应头 `Last-Modified: Wed, 28 Oct 2026 03:11:00 GMT`、`Content-Length: 315489`）。
**本轮全程测的都是 `5161c957…`，不是旧包。**

### 0.1 重启后复验（`docker restart r12-fe` 之后）

team-lead 于本轮收尾时重启了前端容器（约 8 秒）。为排除"重启后换包 / 换配置"的可能，做了一次完整复核：

| 复核项 | 时刻 | 结果 |
|---|---|---|
| entry asset / md5 | 11:26:29、11:30:08 | `index-fup9RT0c.js` / `5161c957f19bb7f1ee825ca33d6771cc` → **与重启前完全一致**（未换包） |
| dist == served | 同上 | 两行 md5 一致 |
| `Last-Modified` / `ETag` | 同上 | `03:11:00 GMT` / `6ae167c4-4d061` 未变 |
| root | 同上 | `200` |
| ② S5-08 三态重跑（真实 UI 重新登录） | 11:2x | 三态文案、presign 状态（404/403/500）、零取流短路 **与重启前逐项一致**，互不相同仍为 true |
| §5 Office 回归重跑（服务端真值 + UI 真值） | 11:2x | **仍成立**：docx/pptx presign 200 后走 `/file/stream` 500；服务端 previewStream 三者 200/PDF；pdf 正常 canvas=1 |

结论：重启未改变任何被测工件，本报告结论对"重启前/后"两个时点均成立。

---

## 1. 判定总表

| # | 项 | 判定 | 一句话结论 |
|---|---|---|---|
| ① | 包内证据：presign 是否在 fileType 分支之前 | **PASS** | 已从线上 entry bundle 抠出，`await presign` 在**所有**类型分支之前（偏移 104 < 118），可在包内确认 |
| ② | S5-08 失败文案三态（详情抽屉） | **PASS** | 三态文案互不相同且可区分：①真实 404 端到端；②③为注入验分支（见 §3 局限） |
| ③ | S5-07 图片预览 | **UNVERIFIED** | kb_9 图片样本 0 个（在线复核），**缺样本**，不借其它 KB 素材凑 PASS |
| 附加 | 额外发现：Office 打开原文回归 | **FAIL（阻断级，超范围）** | 主因=该入口把 Office 投给 `/file/stream`（应走 previewStream）；实测该次请求带 `pageNo/pageSize`，服务端返回**真实 500/5004**（一级证据见 §5）；不带分页参数时服务端 200 返回 **docx 原件 zip**，渲染器按 PDF 解析同样必失败 |

---

## 2. ① 包内证据 — PASS

**做法**：先枚举 `dist/assets/*.js` **全量 874 个 chunk**（避免 ROUND-A 记录过的「只搜 entry = 局部搜索冒充全量」），再用特征串 `缺少原文对象键，无法打开原文` 定位；逐个比对 dist 与线上下发件 md5。

| chunk | 特征串命中 | chars | dist md5 | served md5 | 一致 |
|---|---|---|---|---|---|
| `index-fup9RT0c.js`（entry） | 1 | 305,649 | `5161c957…` | `5161c957…` | 是 |
| `index-legacy-DRXPF9oJ.js`（nomodule） | 1 | 365,526 | `ff9e020e…` | `ff9e020e…` | 是 |

其余 872 个 chunk 均 0 命中 → 该逻辑不存在于 lazy chunk 的**另一份副本**，入口行为可代表抽屉行为。

**包内片段（entry，压缩后，原样）**

接口常量：
```js
as="/proxy/index/knowledgeBase/file/stream",
xr="/proxy/index/knowledgeBase/file/previewStream",
Oo="/proxy/index/knowledgeBase/file/presign",
Mo=["png","jpg","jpeg","gif","bmp","webp"],
Uo=["xlsx","xls","csv"],
$o=t=>!!t&&Uo.includes(t.toLowerCase()),     // isSheetType
zo=t=>!!t&&Mo.includes(t.toLowerCase()),     // isImageType
```

`Go()` = getPresignedObjectUrl（presign + 三态映射）：
```js
Go=async(t,s)=>{const r=Gt(t);if(!r)throw new Error("缺少原文对象键，无法签发地址");
 const a=await fetch("".concat(Oo,"?key=").concat(encodeURIComponent(r)),{method:"GET",headers:{Authorization:s||""}});
 if(!a.ok){ ... a.status===404||u==="10001" ? x="原文不存在或已删除…"
              : a.status===401||403||u==="30016"||u==="30022" ? x="无权访问该原文…"
              : a.status>=500 ? x="原文服务异常（HTTP …）…" : x="原文地址签发失败（HTTP …）" ...}
 ... return l}
```

`qo()` = resolvePreviewTarget（**关键顺序**）：
```js
qo=async({source:t,fileType:s,token:r})=>{
  const a=Gt(t);                                  // getObjectKeyFromSource
  if(!a)throw new Error("缺少原文对象键，无法打开原文");
  const n=await Go(t,r);                          // ← presign：先执行，且 await
  return zo(s)?{filePath:n,streamApiUrl:as}       // 图片
       : lr(s)||$o(s)?{filePath:a,streamApiUrl:xr} // Office/表格 → previewStream
       : {filePath:a,streamApiUrl:as}              // 其它 → stream
}
```

**结构判定（按偏移，不按猜测）**：`qo()` 内 `await Go(` 偏移 = **104**，第一个类型分支 `return zo(` 偏移 = **118** → **presign 在 fileType 分支之前成立**。
即：任何类型都会先 await presign；presign 失败时**不会**再发取流请求。

包内同时含三态文案常量（偏移：`原文不存在或已删除` 98279 / `无权访问该原文` 98381 / `原文服务异常（HTTP ` 98438）。

补充（legacy bundle 同序，一并核对）：`La=t("r",async({source:e,fileType:t,token:r})=>{… const o=await (async(…)={…presign…})(…); …})` —— presign 同样在任何类型分支之前。

**副产品**：本项证明的是「包里有这段逻辑且顺序正确」，**不等于**「所有入口都传对了 fileType」——见 §5 附加发现。

证据：`evidence/bundle-extract.txt`、`evidence/bundle-extract.json`

---

## 3. ② S5-08 失败文案三态（详情抽屉）— PASS

入口：真实 UI 登录 → `/chats/knowledgeBase/9` → 点击文件名 → 打开原文抽屉（左预览 + 右问答面板，与 ROUND-A 同一入口）。

| 子项 | 触发方式 | presign 实际响应 | 页面文案原文 | 判定 |
|---|---|---|---|---|
| ① 原文不存在 | **真实**服务端 404（仅注入列表数据把该行指向不存在的对象键 `r12-rag/kb_9/AG2B-not-exist-fiction.pdf/V0/…`） | `404 {"errorMsg":"知识库文件不存在","errorCode":"10002"}` | `加载失败：原文不存在或已删除（知识库文件不存在）` | **PASS** |
| ② 无权访问 | 注入 presign `403/30016`（admin 为超管，真实 403 不可构造） | `403 {"errorCode":"30016","errorMsg":"无权访问该知识库文件"}` | `加载失败：无权访问该原文（无权访问该知识库文件）` | **PASS（分支可达 + 文案正确；真实 403 未取得）** |
| ③ 原文服务异常 | 注入 presign `500`（不重启/不改配置无法真实触发） | `500 {"errorCode":"5001","errorMsg":"对象存储读取失败"}` | `加载失败：原文服务异常（HTTP 500）：对象存储读取失败` | **PASS（分支可达 + 文案正确；真实 5xx 未取得）** |
| ④ 三态可区分 | — | — | 三条文案 `new Set(...).size === 3` → **互不相同 = true** | **PASS** |
| ⑤ presign 是否前置生效 | — | 三个场景 presign 命中各 1 次，且**失败后完全无 stream/previewStream 请求**（`streamGatedByPresign=true`） | — | **PASS** |

**与 ROUND-A（旧包）对比**：旧包三态被压成统一 `加载失败 / PDF请求失败: 500`，判 FAIL；新包已可区分 → **缺陷 P1-01 的三态部分已修复**。

**必须写明的局限（不掩盖）**
1. 只有 **①原文不存在** 是真实端到端（服务端真实 404/10002，页面文案由其驱动）。
2. **②③** 的 HTTP 状态与 `errorMsg` 是我用 Playwright `route` 注入的**前端响应**；被验证的是「前端映射分支可达 + 前缀文案正确」，**服务端真实 403/5xx 仍未取得**。括号内文案属注入内容，不能当作服务端口径证据。
3. 三态"可区分"成立的前提是 presign 返回 4xx/5xx；若服务端返回其它码，仍会落 `原文地址签发失败（HTTP xxx）` 第四态（包内存在，本轮未构造）。
4. 本条只判**失败文案**，不判打开原文明细是否可用 —— 见 §5。

证据：`evidence/S5-08-1-notfound/{result.json,02-drawer.png,03-drawer-pane.png}`、`evidence/S5-08-2-denied/*`、`evidence/S5-08-3-5xx/*`、`evidence/s5-08-results.json`

---

## 4. ③ S5-07 图片预览 — UNVERIFIED（缺样本）

在线复核（走页面登录态，真实接口 `folder/list`，11:2x）：

| 指标 | 值 |
|---|---|
| kb_9 文件数 | 10 |
| 扩展名分布 | pptx 2 / pdf 3 / docx 4 / xlsx 1 |
| 图片类文件（png/jpg/jpeg/gif/bmp/webp） | **0** |
| 接口 `imagePaths` 汇总 | **0** |

→ **缺样本，UNVERIFIED**。未使用任何替代素材、未上传、未写入 kb_9。
信息性登记（**不作为本条判定依据，也未借用**）：其它 KB 存在图片夹具 —— `kb 10 / qa_r12_final` 与 `kb 5 / qa_r12_indep` 各有 `scan-text.png`。若后续要补测本条，应由写权限角色在独立批次/独立 KB 提供夹具后重跑；本轮"不借素材凑 PASS"。

证据：`evidence/S5-07-image/{result.json,kb9-inventory.json,other-kb-image-scan.json,01-kb9-list.png}`

---

## 5. 附加发现（超范围，但阻断级，必须上报）

### 附加-1｜Office 类型"打开原文"在新包上失败（回归）— FAIL

**现象（新包 `5161c957…`，真实 UI 操作，无注入）**

| 文件 | presign | 实际取流接口 | 请求体 | 结果 | 页面 |
|---|---|---|---|---|---|
| `docx-plain.docx` | 200 | `POST /proxy/.../file/stream` | `{"convertedFilePath":<key>,"pageNo":1,"pageSize":5}` | **500** 74 B JSON | `加载失败 / PDF请求失败: 500`，canvas=0 |
| `R12FIX-product-intro.pptx` | 200 | `POST /file/stream` | 同上形状 | **500** 同上 | 同上，canvas=0 |
| `pdf-digital.pdf` | 200 | `POST /file/stream` | 同上形状（含 pageNo/pageSize） | 200 `application/octet-stream` | canvas=1 正常 |
| `R12FIX-credit-ledger.xlsx` | 200 | `POST /file/stream` | 同上形状 | 200 | 无失败文案，canvas=0（内容未复核，超范围不判） |

**一级证据：页面自己那一次请求的 payload 与响应原文（截获方式：`route.fetch` 透传观测，请求/响应均未修改，仅留副本）**

```text
REQ  POST /proxy/index/knowledgeBase/file/stream
     Authorization: <有，仅记长度>        X-Platform: 无
     payload = {"convertedFilePath":"r12-rag/kb_9/docx-plain.docx/V0/docx-plain.docx","pageNo":1,"pageSize":5}
RES  500   content-type: application/json   body 74 B
     {"success":false,"errorMsg":"参数非法","errorCode":"5004","data":null}
```

→ **这个 500 是接口返回的，不是渲染器抛的**：状态码 500、`content-type: application/json`、body 是后端统一错误结构（`success/errorMsg/errorCode`），且由透传观测在**未修改**的前提下取得。页面文案 `PDF请求失败: 500` 与之一致，但报告结论不依赖页面文案。

**参数矩阵（同键、同登录态、页面内 fetch 重放；用来定位 500 的触发因子）**

| # | 接口 | 请求体 | 结果 | 关键字节 |
|---|---|---|---|---|
| A | `stream` | `{convertedFilePath}` | **200**，36,716 B，`application/octet-stream` | magic `50 4b 03 04` = **PK（docx 原件 zip）** |
| B | `stream` | `{convertedFilePath, pageNo:1, pageSize:5}` | **500**，74 B，JSON | `{"errorMsg":"参数非法","errorCode":"5004"}` |
| C | `stream` | `{filePath: <key>}` | 200，112 B，JSON | `999 NotBlank[convertedFilePath]文件地址不能为空` |
| D | `stream` | `{}` | 200，112 B，JSON | `999 NotBlank[convertedFilePath]…` |
| E | `previewStream` | `{convertedFilePath}` | **200**，29,393 B，`application/pdf` | magic `25 50 44 46` = `%PDF-1.7` |
| F | `previewStream` | `{convertedFilePath, pageNo:1, pageSize:5}` | **200**，29,393 B，`application/pdf` | `%PDF-1.7` |

矩阵结论（**同时解释 team-lead 的两次观察，两者都对，差别在请求体**）：

- **A 行复现 team-lead 的 200 + zip**：不带分页参数时，`stream` 对 docx 返回**原件 zip 字节**（不是 PDF）。
- **B 行复现页面实际那次 500**：页面/读取器在体里**多带了 `pageNo/pageSize`**，服务端对这一组合返回**真实 500/5004「参数非法」**。
- **C 行复现 team-lead 的 999 NotBlank**：参数名写错（`filePath`）得到的是 999，不是 500/5004 —— 说明 500/5004 与"参数名错"无关，是"`stream` + 二进制 docx + 分页参数"这一组合触发。
- E/F 行：`previewStream` 带不带分页参数都是 200 + `%PDF-1.7`（服务端转换能力完好）。
- 对照：`pdf` 用 B 行同样的体（含 `pageNo/pageSize`）→ 200 原始字节，说明分页参数本身不必然 500，**是"二进制文档 + 分页"的组合不合法**。

**因此归因分两层，修复位置不同**

1. **主因（必须修）：分流错误** —— 该入口把 Office 投给了 `/file/stream`。即便服务端不 500（A 行情形），拿到的也是 **zip 原件**，渲染器按 PDF 解析必然失败 —— 这正是 team-lead 说的 (b)。路由应走 `previewStream`（E/F 行 200/PDF）。
2. **次因（叠加，属接口口径问题）** ：读取器对 `stream` 附带了 `pageNo/pageSize`，服务端对该组合直接 500/5004，使失败提前到接口层。若只修服务端口径而不修分流，页面仍会因"zip 当 PDF"失败；若只修分流，这两个参数根本不会到达 `stream`。**以修分流为主。**

→ 服务端能力完好（`previewStream` 对 Office/表格均返回转换后 PDF）；缺陷在**该入口的分流选择**，并叠加了 `stream` 对分页参数返回 500 的口径问题。

#### 5.1 为什么"用干净键直打服务端得到 200"不能反驳本条的 500（供后人对照，防误读）

一句话：**差别不在键的形态，而在请求体里是否带 `pageNo/pageSize`。**

- **事实（一级证据）**：该入口实际发出的 `convertedFilePath` 就是**裸对象键** `r12-rag/kb_9/docx-plain.docx/V0/docx-plain.docx` —— 同一轮的 `presign` 的 `key=` 参数也是同一个裸键；请求体中**没有** `/preview/convert?key=`、**没有** `/minio/` 前缀、**没有** URL 编码。取原文见 `evidence/diag4/diag4.json` → `phaseA_uiClick.pairs[1].request.payloadRaw`。
- 因此"干净键 → 200"对应矩阵 **A 行**（无分页参数），而页面走的是矩阵 **B 行**（带 `pageNo:1,pageSize:5`）→ 同一裸键，前者 200+zip，后者 500/5004。
- **同时排除另外两种历史失败面**（见 `StreamReader.tsx:14-20` 注释所列）：本条错误码是 `5004 参数非法`，**不是** `403/30016`（`assertStreamAllowed` 按 `/` 切段找不到 `kb_xxx`），**也不是** `500 getInputStreamByUrl failed`（`/minio/` 前缀未剥离）。故以"键形态"解释本条 500 与证据不符。
- 复核口径：若要验证本结论，比对 `diag4.json` 中 `phaseA_uiClick.pairs[1]` 的 `payloadRaw` 与 `phaseB_matrix` 的 A/B 两行即可，无需重跑 UI。

**旧包基线（ROUND-A，同一入口、同一文件）**：`POST …/previewStream` **200 / `application/pdf` / 29,393 B**，canvas=1，页码 `1 / 1` 正常渲染（`AG-2/evidence/S5-03-docx-plain/result.json`）。
→ 故这是**新包引入的回归**，不是"本来就这样"。

**根因（推断，非事实；未做组件级断点验证）**：包内 `qo()` 只有 `lr(fileType)||$o(fileType)` 为真才走 previewStream；实测走了 stream，说明该入口传给 `resolvePreviewTarget` 的 `fileType` **未命中 Office 集合**。

- **修复点已由 team-lead 交叉确认**：`FileViewCom.tsx:113-120` 把 `target.streamApiUrl === PREVIEW_STREAM_API ? "pdf" : meta.fileType` 传给 `StreamReader` —— 即**分流结果在 `resolvePreviewTarget` 处已被定死**，一旦判成 `stream`，下游一路错下去。故修复点是 **`resolvePreviewTarget` 的入参 `fileType`**，**不要改 `StreamReader`（那是下游）**。
- 仍属推断、未证实的部分：**具体哪个调用方**传了错误的 `fileType`。注意本入口实测传的是**裸键**（非 `/preview/convert?key=…` 形态），而 `DrawerPreview.tsx` / `FileViewCom.tsx` 已改为"优先用源文件名后缀判类型"，故不能直接把本入口等同于这两个组件；`DrawerContent.tsx` 仍用 `getFileType(curContent, filePath)` 推断，是候选之一但未验证。**定位到具体调用方需要 React props 级断点，本轮未做。**

**影响**：阻断。Office（docx/pptx）在"文件列表 → 点击文件名"入口**打不开原文**，且失败文案与"原文服务异常"同形（`PDF请求失败: 500`），会误导用户与后续验收。
**建议**：修复后重测 **S5-03（docx）/ S5-05（pptx）**，并复查 S5-08 的正/负例不再互相混同。**本项不计入本轮三项判定**（派工明确"不扩范围"），但因其为阻断级，按纪律照实上报。

证据：`evidence/diag3/server-truth.json`、`evidence/diag3/ui-truth.json`、`evidence/diag3/ui-docx-plain.docx.png`、`evidence/diag3/ui-R12FIX-product-intro.pptx.png`、`evidence/diag2/diag2.json`

---

## 6. 注入 / 绕行清单（合规声明）

| # | 类型 | 位置 | 内容 | 是否影响判定 |
|---|---|---|---|---|
| 1 | **注入式绕行** | 登录后「密保问题设置」强制弹窗 | 仅从 DOM 移除 `.ant-modal-wrap`（按 innerText 精确匹配"密保问题设置"，不碰其它 Modal）；**未点击「确 定」「退出登录」，未触达服务端**；`kills=1`/场景 | 不影响；弹窗存在本身记录为环境事实 |
| 2 | 注入（数据） | `folder/list` 响应（仅 S5-08-①） | 把 `docx-plain.docx` 行改为不存在的对象键 `…/AG2B-not-exist-fiction.pdf/V0/…` | 仅造样本；**服务端 404/10002 为真实响应** |
| 3 | 注入（响应） | `presign`（仅 S5-08-②） | 返回 403 + `errorCode 30016` | 已在 §3 局限中标注；不计作服务端证据 |
| 4 | 注入（响应） | `presign`（仅 S5-08-③） | 返回 500 + `errorCode 5001` | 同上 |
| 5 | **透传观测（不是注入）** | `POST /knowledgeBase/file/stream`（仅 §5 一级证据采集那一次） | `route.fetch()` 取副本 → **原样 `fulfill`**，请求体、响应状态/头/字节均未修改，仅旁路留证 | 不改变被测行为 |
| 6 | 未做 | — | 未改源码、未改配置、未改 dist、未重启服务、未建库/删档/上传 | — |

登录方式：**真实 UI 登录**（`/login` 填 admin / Admin@12345 + 服务端验证码），验证码取自 Redis（与图片同一份，等价人工识图，未关闭/降级服务端校验）；登录响应 `HTTP 200 success=true`，token 长度 237。**未使用 token 注入登录态**（与 ROUND-A 的 localStorage 注入方式不同）。逐场景记录见各 `login-record.json`。

---

## 7. 自检（本报告的自我质疑）

1. **锚点自证**：md5 在开始（11:11:20）与收尾（11:25:34）各比一次，dist 与线上取回一致且 ≠ 旧值；`Last-Modified` 与 dist mtime 一致 → 测的是新包本体，不是缓存/fallback。
2. **没有用 mtime 代替包内证据**：① 的结论来自 bundle 内偏移比较（104 < 118）+ 全量 chunk 枚举；mtime 只写在 §0 作为代次标记。
3. **没有把"包里有"当成"页面行为对"**：① 的 PASS 只覆盖"顺序正确"；②③ 的行为另测；§5 的回归正是"包内有正确代码、入口却传错 fileType"的反例，二者不互相替代。
4. **三态没有夸大**：②③ 明确标为注入，真实服务端 403/5xx 未取得，未据此声称服务端契约已验证。
5. **三态"可区分"没有只看代码**：以页面实际渲染文案取原文比对（`new Set` 三条互不相同），并留截图与 DOM 文本。
6. **没有借素材**：S5-07 判 UNVERIFIED，明知 kb 5/10 有 `scan-text.png` 仍不借用。
7. **单点失败不当全局**：§5 的 Office 回归用 docx **与** pptx 双样本复现，并用服务端真值（previewStream 200/PDF）排除"服务端坏了"。
7.1 **不用页面文案反推接口状态**（team-lead 复核后补做的一级证据）：§5 的 500/5004 由**透传观测**（`route.fetch` → 原样 `fulfill`，未修改请求/响应）拿到页面那一次请求的 `payload` + `status` + `body` 原文；另用 6 行参数矩阵定位触发因子（A 行复现 200+zip、B 行复现 500/5004、C 行复现 999），未依赖"页面显示了 500"这一二手现象。
7.2 **归因两处并列，不混为一谈**：先把"分流错误（Office 被投给 stream）"与"stream 对分页参数返 500"分开陈述，再给修复优先级；避免把 team-lead 的 200+zip 与我的 500 当成互相否定——两者是**同一接口不同请求体**的两个真实结果。
8. **遗留未验证（明确列出，避免下游误读）**：
   - 服务端真实 403（越权）与真实 5xx 未取得 → ②③ 的服务端口径未验证；
   - xlsx 在新包上的表格内容未复核（超范围）；
   - Office 回归的组件级根因未做运行时定位（仅代码推断）；
   - `原文地址签发失败（HTTP xxx）` 第四态未构造。

---

## 8. 证据索引（相对 `AG-2B/evidence/`）

```
00-build-anchor.txt                包锚点：md5 / mtime / 响应头
bundle-extract.txt / .json         ① 包内片段 + chunk 全量枚举 + 偏移判定
s5-08-results.json                 ② 三态汇总（timeline / 文案 / 短路）
S5-08-1-notfound/                  ② 真实 404：result.json + 02-drawer.png + 03-drawer-pane.png + login-record.json
S5-08-2-denied/                    ② 注入 403/30016：同上
S5-08-3-5xx/                       ② 注入 500：同上
S5-07-image/                       ③ kb_9 清单 + 全库图片扫描（信息性）
diag3/server-truth.json            §5 服务端真值（presign/previewStream/stream 三接口同键对照）
diag4/diag4.json                   §5 一级证据：页面请求 payload + 响应 body 原文（透传观测）+ 6 行参数矩阵
diag4/01-docx-click.png            §5 失败页面截图
diag3/ui-truth.json                §5 UI 真值（docx/pptx/xlsx/pdf 四类实际取流接口）
diag2/                             §5 docx vs pdf 细粒度请求体与响应
diag/                              入口结构探查（抽屉识别、kb_9 列表）
```

脚本（可复跑）：`AG-2B/scripts/{ag2b_lib.js, extract_bundle_evidence.py, s5_08_states.js, s5_07_image.js, diag3_server_vs_ui.js, diag2_stream_detail.js, diag_detail_drawer.js}`
