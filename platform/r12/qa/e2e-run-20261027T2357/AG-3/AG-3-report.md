# AG-3 验收报告 · 问答 local（S7）+ 检索测试（S6）

角色：AG-3（只读：只提问 / 只检索，不建库、不删档、不重启服务、不改配置）
运行目录：`/home/szf/data/dev/llmke-r12/platform/r12/qa/e2e-run-20261027T2357`
证据根：`AG-3/evidence/**`　脚本：`AG-3/scripts/**`
报告时刻：2026-10-28 10:50（本机时间）

---

## 0. 第 0 步自证（§1.4，我本人跑的两端）

```
entry        assets/index-CpE2zvYY.js
线上取回     curl http://127.0.0.1:18088/assets/index-CpE2zvYY.js  → 315576 字节
线上 md5     de2424501bd29e358043049876db2a75
宿主 md5     de2424501bd29e358043049876db2a75   → 相同（非 23KB SPA fallback）
收工复核     /tmp/served-AG3-end.js md5 = de2424501bd29e358043049876db2a75（同一版）
```

服务代次（R5，开工与收工各记一次，**完全一致**）：

```
8088=1403651  18082=2139785  18083=1647331  19527=1823402  19529=1461792  19995=1481869
```

结论：本次测的是 `de2424501bd29e358043049876db2a75`，全程无服务重启/换代次，无 ENV_EVENT 窗口。

### 0.1 版本漂移的边界（采纳 AG-2 的发现，修订我自己先前的话术）

§1.4 的 md5 自证只证明**「宿主 dist == 服务端下发的 dist」**，**不证明 dist 由当前 HEAD 构建**。AG-2 已证实：

```
dist/assets/index-CpE2zvYY.js   构建 2026-10-27 13:22
src/core/components/StreamReader.tsx 改动 13:35
fix(r14-D) 提交               16:19（HEAD=303b12e 17:27）
证据：AG-2/evidence/version-check/{version-selfcheck.txt,served-bundle-StreamReader.txt}
```

我据此复核了**我自己**引用到的"源码归因"是否成立。注意搜索范围：**不只 entry，而是全量 874 个 chunk**
（`frontend/plateform/dist/assets/*.js`）——只搜 entry 会漏掉懒加载 chunk，这是本轮已经踩过的坑：

```
"parsed/tables"         → 0 个文件命中（entry + 874 chunk 全量）  ← 前端不拼这个键
"file/presign"          → 只有 entry(CpE2zvYY) 与 index-legacy 命中（2 个文件）
"预览分支"               见下方 nh 反编译，字面量存在 ≠ 该分支会调 presign
"重拍模型"               → 0 次  ← 这句提示来自服务端 msg，不是前端文案
```

**AG-2 提醒后我改正的一处行为层误判（重要）**：我先前写"旧包也走 presign + xlsx 分支"，
这在**字面层**成立、**行为层不成立**。AG-2 从线上 entry 抠出的 `resolvePreviewTarget`（压缩名 `nh`）真实实现是：

```js
nh = async ({source, fileType, token}) => {
  const a = It(source);                                  // getObjectKeyFromSource
  if (!a) throw new Error("缺少原文对象键，无法打开原文");
  return xs(fileType) || Go(fileType)                     // office(docx/pptx) 或 sheet(xlsx/xls/csv)
    ? { filePath: a, streamApiUrl: ns }                   // ← 直接 return，**不调 presign**
    : gr(fileType)
      ? { filePath: await os(source, token), streamApiUrl: wt }          // 图片 → presign
      : (await os(source, token), { filePath: a, streamApiUrl: wt });    // 其它 → presign
};
```

`Go` 就是 `["xlsx","xls","csv"]` 那个数组——**它在包里，但所在分支排在 `return` 之后**，
所以"包里有 xlsx 分支"推不出"xlsx 会走 presign"。我实测到的表格引用 presign 调用**不是 `nh` 发的**，
而是表格块引用那条链路自己直接调了 `getPresignedObjectUrl`（见 P1-1 的"为什么会调 presign"）。
结论方向不变（那条路径确实调了、且键错），但**归因不能写成"旧包 xlsx 分支会走 presign"**——
那样会让修复方去改 `nh` 的 sheet 分支，改完仍然 404。

对判定的影响（我已按下述口径改写 §3 P1-1 的归因，不把"源码=运行代码"当默认前提）：

- **不受影响**：所有以 HTTP 事实为准的判定（presign 404/10002、previewStream 200、505 采样、答案文本），
  这些都是我从线上实际抓到的，与"包是不是最新"无关。
- **受影响**：任何"前端某文件这么写的所以如此"的推断。因此 P1-1 的归因已改为
  "bundle 内无 `parsed/tables` 字面量 + Java 侧 `Document.java:82` 生成该路径"这一**包内可复核**的链条，
  不再依赖 `fileAccess.ts` 的当前源码。
  **最终根因见 P1-1 修订版：不是"服务端 `parsed` 副产物口径与实际落盘不一致"，而是
  引用链路拼的表键缺 `table-N-` 序号前缀（对象真名 `tables/table-0-授信台账.md`，链路拼 `tables/授信台账.md`），
  且没有复用服务端已公布的 `tableFilePaths`。**（AG-2 对照 + TL 独立复核 + 我独立复跑键矩阵，三方一致）
- **不采用 r14-D 的"已修复"作为期望值**：我全篇的期望值写的是产品应有行为（"点引用应能看见原文"），
  不是"r14-D 声称修好了"。所以不存在"照已修复版写期望值"的误判。

### 0.1b 方法局限：字面量计数不能证明"这条路径会走到它"

我在 §0.1 用 `grep` 数 bundle 里的 `presign` / `previewStream` / `parsed/tables` 字面量，**只能证明"代码在包里"，
不能证明"某条路径执行到了它"**。AG-2 已经踩过这个反例：`presign` 与 `previewStream` 在包里都命中，
但详情页两条抽屉就是不调 presign。

因此本报告的证据分级：

```
一级（可作判定依据）  HTTP 请求/响应的实测记录（page.on('response')、net.json、presign 404 body、
                      直接 requests 的键矩阵）、页面可见内容（截图/canvas 采样/文本）
二级（只能作佐证）    bundle 字面量 grep、源码阅读
→ 凡"某条路径调不调某某接口"的结论，必须以一级证据为准；二级只用来解释"为什么"
```

我把上面那句"前端 bundle 里没有 `parsed/tables` 字面量 → 该路径来自服务端"标为**二级证据**，
它的作用是解释方向；P1-1 的判定本身靠的是一级证据（B 键 presign 404、C 键 200、folder/list 公布 C）。
别让"字面量计数"变成新一代的"搜到了就算查过"。

这条规则覆盖本轮出现的**五类同型事故**（都是"用弱证据替代强证据"，与 AG-2 的编号对齐，可直接进合并稿）：

```
① 只 grep 一个模式就下结论         → 该模式可能只存在于另一个入口/分支
② 只搜 entry chunk 就下结论         → 懒加载 chunk 里的代码根本没搜到（我第一版就只搜了 entry，已改为全量 874 chunk）
③ 用一条路径的结论覆盖另一个入口     → 详情页预览 PASS 被推成"xlsx 预览都正常"，
                                      或反过来"引用链路 FAIL"被推成"xlsx 预览都断了"
④ 拿 src 当"线上包必然如此"         → 我第一版 P1 归因写了 fileAccess.ts（源码），
                                      而运行包落后于该源码；现改为"包内可 grep + HTTP 实测"
⑤ 采集端污染被当成产品现象           → 我把 SSE 用 r.text() 抓成文件时中文被二次编码，
                                      一度以为服务端 parsedFilePath 里的表名是乱码；
                                      回 raw bytes 复核后确认是**我自己抓取的解码问题**，不是产品缺陷，已撤回
→ 共同解药：判定只认一级证据，一级证据必须带"路径域"，且**字符串类证据一律回 raw bytes 复核**
```

**①② 最典型的反例（AG-2 提供，我写进规矩）**：
**字面量能证明代码存在，不能证明该分支被执行；分支内 `return` 顺序要读，不能只看符号是否存在。**
`Go`（`["xlsx","xls","csv"]`）数组确实在 `nh` 里，但它所在的三元分支排在 `return` 之前就短路了，
所以 sheet 类型根本不会走到 `presign` —— 符号在、路径不在。

**③ 最典型的反例（我自己这轮踩的）**：
我用"某处有 presign"推到"由哪个组件发起"，中间没有一级证据；后来用**调用点穷举 + 排除法**才收敛
（见 P1-1"为什么会调 presign"）。只做过一次观测就把结论摊到两个组件上，是本轮第三次同型错误。

### 0.2 会话建立方式披露（注入式绕行，按协调者统一口径）

```
方式        注入式会话建立：用 /auth/user/simpleLogin 取**服务端签发**的真实 token，
            按前端 AppPassport 约定写入 localStorage["gitech_ril:rag_ai"].userInfo.token
            与 cookie rag_ai_token；必须在页面脚本执行前注入（addInitScript），
            否则 getTokenLocal() 会立刻 window.location.pathname="/login"。
未伪造      token 为服务端签发；未伪造接口返回；未改服务、未改配置、未改库。
未覆盖      图形验证码登录流程本身（S1）→ 见 §4 UNVERIFIED，由 AG-1 单点覆盖。
未触发密保  我未走通 UI 登录，也就没遇到 AG-1 说的「密保问题设置」强制弹窗；
            我的会话是注入式，因此**不触发该弹窗，也未提交任何密保设置**（无写操作）。
```

---

## 1. 一页总表

| 场景 | 判定 | 断言通过/总数 | 耗时 | 关键证据 |
|---|---|---|---|---|
| §1.4 前端版本自证 | PASS | 1/1 | <5s | 本节哈希 |
| S7-1 语料内提问→有答案+有引用（接口层） | PASS | 1/1 | 11.8s | `evidence/api/S7-chat-20261027T160318Z.json` |
| S7-2 引用可回指·三段全绿（接口层，3 条） | PASS | 3/3 | 含上 | 同上（形态/presign/get200/版本 逐条） |
| S7-3 点引用→打开原文且**页面看见内容**（docx） | PASS | 1/1 | 5s | `S7-ui/u1-03-citation-open.png`、`S7-ui/U1-network.json` |
| S7-4 点引用→打开原文（**引用链路 · 表格块 → 表格文件**） | **FAIL** | 0/1 | 4s | `evidence/probe-xlsx/net.json` |
| S7-5 语义改写两次（接口层） | PASS | 2/2 | 26s | `evidence/api/S7-chat-*.json` → `rephrase.A/B` |
| S7-6 语义改写（UI） | PASS | 1/1 | 21s | `evidence/S7-ui2/U2_rephrase.json` |
| S7-7 多轮上下文（接口层） | PASS | 1/1 | 12s | `evidence/api/S7-chat-*.json` → `multiturn` |
| S7-8 多轮上下文（UI） | PASS | 1/1 | 57s | `evidence/S7-ui3/U3_multiturn.json` |
| S7-9 刷新后历史恢复（严格：本轮唯一标记 + sessionId） | PASS | 1/1 | 41s | `evidence/S7-hist/U4_history_strict.json` |
| S7-10 同问连跑 3 次（接口层） | PASS | 1/1 | 41s | `evidence/api/S7-chat-*.json` → `repeat3` |
| S7-11 同问连跑 3 次（UI） | PASS | 1/1 | 68s | `evidence/S7-ui/U5_repeat3.json` |
| S7-12 取消生成 | **FAIL** | 1/2 | 45s | `evidence/S7-ui3/U6_cancel.json` |
| S6-1 混合检索 | PASS | 1/1 | 1.3s | `evidence/api/S6-retrieval-20261027T160318Z.json` |
| S6-2 纯全文（ES） | PASS | 1/1 | 0.1s | 同上 |
| S6-3 纯向量（Milvus） | PASS | 1/1 | 2.1s | 同上 |
| S6-4 同 query 连跑两次一致性 | PASS | 1/1 | 1.6s | 同上 `consistency` |
| S6-5 无结果 query → 明确"无结果"不报错 | PASS | 1/1 | 1.7s | 同上 `no_result.rerank_on` |
| S6-6 表格类文件可被检索到（跨索引） | PASS | 1/1 | 3.1s | 同上 `table_cross_index` |
| S6-7 结果 pk 存在于当前 ES | PASS | 1/1 | <1s | 同上 `pk_existence`（3/3） |
| 数值断言 8000 万可在引用原文中找到 | PASS | 1/1 | — | `S7-ui/u1-03-citation-open.png` |

合计：**PASS 19 / FAIL 2 / INFO 1 / BLOCKED 0 / UNVERIFIED 2 / NOT RUN 2（见 §4）**

> 表内 22 条是我**能判**的断言；另有 2 条因"注入式会话绕行"未覆盖（图形验证码登录流程、密保弹窗对业务的影响），
> 单列在 §4 并按 UNVERIFIED 处理，**不记 PASS、不进本表分母的 PASS 数**。

---

## 2. 每条明细

### S7-1 / S7-2 语料内提问 + 引用三段全绿（接口层）

```
场景：S7 问答 local（configId=1）
前置：admin 已登录；kb_9 就绪；服务 pid 见 §0
步骤：
  1) POST http://127.0.0.1:8088/qa/ai/question
     {"sessionId":"ag3-…","queryId":"ag3q-…","content":"智造贷最高授信额度是多少？",
      "type":"text","sysType":"KNO_INDEX","configId":1}，Accept: text/event-stream
  2) 解析 SSE：最后一次 reply.content + reference.documents
  3) 每条引用三段：①source 形态 ②presign(key)=200 且签名URL GET=200（记字节）
     ③source 的 /Vn/ == 该文件当前有效版本（按 /V 之前前缀归一，§5 陷阱1）
期望：status=2；答案含"8000 万"；≥1 条引用；每条三段全绿
实际：http=200 status=2 answer="智造贷单户最高授信额度为人民币8000万元。" refs=3 elapsed=11.8s
      ref0 form=ok presign=200 get=200 bytes=37543 ver=V1/有效V1 → 绿
           source=r12-rag/kb_9/R12FIX-product-loan.docx/V1/R12FIX-product-loan(1).docx
      ref1 form=ok presign=200 get=200 bytes=29388 ver=V1/有效V1 → 绿
           source=r12-rag/kb_9/R12FIX-product-intro.pptx/V1/R12FIX-product-intro(1).pptx
      ref2 form=ok presign=200 get=200 bytes=5340  ver=V0/有效V0 → 绿
           source=r12-rag/kb_9/R12FIX-credit-ledger.xlsx/V0/R12FIX-credit-ledger.xlsx
           （台账只有 V0，"V0"就是有效版本，不是旧稿）
判定：PASS
证据：AG-3/evidence/api/S7-chat-20261027T160318Z.json（q1.citation 逐条·含 presign_trace/es_hit_indexes）
复跑：platform/r12/venvs/alg/bin/python \
      platform/r12/qa/e2e-run-20261027T2357/AG-3/scripts/ag3_api_probe.py
```

**判据自检**：若引用真落在 V0 旧稿，第③段会红（我按 `/V` 前缀归一取最大版本，不按 title 比，避免"恒真"）。
同时留痕一条我自己造成过的**假红**：第一版 `es_all_sources()` 只读主索引，台账 source 取不到有效版本 →
被我自己判成 `version_ok=False`；改跨三索引（§1.6）后转绿。

### S7-3 点引用 → 打开原文且页面看见内容（docx，历史阻断项）

```
步骤：UI /chats/main → 选助手"R12默认问答配置" → 输入"智造贷最高授信额度是多少？"→ Enter
      → 等"知识溯源"出现 → 点"知识溯源 1" → 点右栏条目 R12FIX-product-loan.docx
期望：抽屉里**看得见正文**（§1.9 以可见内容为准，不判状态码）
实际：网络 previewStream → 200 application/pdf
      抽屉 #pdfBox 存在；canvas=1；左上 50×50 采样 alpha>0 像素 = 2500（非空白渲染）
      文本层："R12FIX-product-loan.docx / 1 / 1 / 111%"
      正文可见："“智造贷”企业流动资金贷款产品说明书… 单户最高授信额度为人民币 8000 万元…"
判定：PASS
证据：AG-3/evidence/S7-ui/u1-03-citation-open.png（截图内可见原文正文）
      AG-3/evidence/S7-ui/u1-04-citation-content.png
      AG-3/evidence/S7-ui/U1-network.json（{status:200, type:application/pdf} + canvas 采样）
复跑：NODE_PATH=/home/szf/.local/lib/node_modules/@playwright/cli/node_modules \
      node platform/r12/qa/e2e-run-20261027T2357/AG-3/scripts/ag3_s7_ui.js
```

### S7-4 点引用 → 打开原文（**引用链路 · 表格块 → 表格文件**）——**FAIL**

```
步骤：UI /chats/main → 问"华东精密制造的授信额度是多少？"（答 3000 万元，"知识溯源 3"）
      → 点"知识溯源" → 点右栏 R12FIX-credit-ledger.xlsx
期望：抽屉里看见台账原文
实际：抽屉显示 "加载失败：原文不存在或已删除（知识库文件不存在）"，无 #pdfBox/canvas
      前端实际发出的请求：
        GET /proxy/index/knowledgeBase/file/presign
            ?key=r12-rag/kb_9/R12FIX-credit-ledger.xlsx/V0/parsed/tables/授信台账.md
        → 404 {"success":false,"errorMsg":"知识库文件不存在","errorCode":"10002"}
      我对同一 key 直连复核：404/10002（对象确实不存在，不是前端编码问题）
      同一文件的可存在键直连复核：
        .../V0/parsed/R12FIX-credit-ledger.xlsx.txt → 200
        .../V0/R12FIX-credit-ledger.xlsx            → 200（真实对象）
判定：FAIL（§1.5 第②段红：presign ≠ 200；用户看不到任何内容）
证据：AG-3/evidence/probe-xlsx/net.json、probe-xlsx/xlsx-drawer.png、
      AG-3/evidence/S7-ui2/U7_table_citation.json、u7-table-opened.png
```

### S7-5 / S7-6 语义改写（同义不同问法，两次）

```
接口层：
  A "请问智造贷这款产品能给到的最高贷款额度是多少"
    → "智造贷产品的最高贷款额度为8000万元。其中信用部分不超过1000万元，其余部分需通过
       应收账款质押、设备抵押或核心企业保证等方式增信。"（refs=3）
  B "智造贷最多可以批多少授信"
    → "“智造贷”单户最高授信额度为人民币8000万元。其中信用方式授信额度不超过1000万元，
       其余部分需…增信。"（refs=3）
UI 层（新会话）："智造贷这款产品最多能给企业批多少授信额度？" → 8000 万元，refs=1，21.3s
关键点一致性：额度口径一致（8000 万）、信用部分上限一致（1000 万）、增信方式一致；
差异仅在措辞与是否复述"单户"字样（A 未写"单户"，B/UI 写了）。
判定：PASS（2/2 接口 + 1/1 UI）
证据：api/S7-chat-*.json（rephrase.A / rephrase.B）、S7-ui2/U2_rephrase.json
```

### S7-7 / S7-8 多轮追问上下文

```
接口层：同一 sessionId 连发两问
  turn1 "智造贷是什么产品？" → 有答案，refs=2
  turn2 "它的最高授信额度是多少？" → "最高授信额度为人民币8000万元。" refs=3
UI 层（同一会话；按"知识溯源"出现次数判定新一轮完成，不用固定 sleep 判完成）：
  turn1 "智造贷是什么类型的产品？" → 31.2s，"…面向制造业中小微企业的企业流动资金贷款产品…" refs=2
  turn2 "它的最高授信额度是多少？" → 26.2s，"最高授信额度为人民币8000万元。" refs=1
期望：第二问的代词"它"解析到第一问实体（智造贷）
实际：两处都落到 8000 万（若代词丢失，答案会跳到产品域外或答"无法确定指代"）
判定：PASS（1/1 接口 + 1/1 UI）
证据：api/S7-chat-*.json（multiturn）、S7-ui3/U3_multiturn.json、u3-turn1.png / u3-turn2.png
```

### S7-9 刷新后历史恢复（严格判据，不写死会话名）

```
步骤：
  1) 新建会话，提一个**本轮唯一标记**的问句："AG3HIST498491 智造贷最高授信额度是多少？"
     （标记由运行时刻生成，本轮唯一，不靠写死会话名）
  2) 抓 createDialogue：sessionId=7f7e643757d3d7b8e35f36ff8bbd1de7
                      queryId=query-643757d3d7b8e35f36ff8bbd1de7e65e
  3) 刷新页面 → 侧栏按该标记命中 → 点击
期望：命中本轮会话（服务端按 sessionId 取详情），答案与"知识溯源"都恢复
实际：sidebarHit=true，clicked=true
      刷新后请求：GET /proxy/qa/dialogue/getDialogBySessionId?sessionId=7f7e643757d3d7b8e35f36ff8bbd1de7
      恢复内容：含 8000 万、含"知识溯源"、含本轮标记
判定：PASS
证据：AG-3/evidence/S7-hist/U4_history_strict.json、u4-1-answered.png、u4-2-restored.png
```

### S7-10 / S7-11 同问连跑 3 次，答案与引用条数波动

```
接口层（"智造贷最高授信额度是多少？"）：
  run1 11.4s len=70 refs=3 | run2 13.6s len=17 refs=3 | run3 14.0s len=22 refs=3
  三次均 8000 万口径；refs 稳定 3；回答长度 17~70 字波动（是否复述"信用部分 1000 万"）
UI 层（每次新建会话）：
  run1 23.2s refs=1 | run2 21.3s refs=1 | run3 23.2s refs=1，三次均 8000 万
期望：结论稳定；引用条数波动只记录不判错
实际：结论 3/3 稳定；refs 接口层稳定 3、UI 层稳定 1（两条路径差异见 §5 O-2）
判定：PASS（1/1 接口 + 1/1 UI）
证据：api/S7-chat-*.json（repeat3）、S7-ui/U5_repeat3.json、u5-run1~3.png
```

### S7-12 取消生成——**FAIL（入口存在、流确实中断、但无终态）**

```
步骤：
  1) 新建会话，发"请详细介绍一下智造贷的适用对象、期限、利率和增信方式"
  2) 2.5s 后（"深度思考中"态）点发送区右侧停止按钮
     实测该控件 = 底部 46×46 的 svg（circle + rect，x=1392,y=935）；
     idle 态同位置才是 lucide-arrow-up（20×20）——两者不是同一个元素
  3) 连续 15s 每秒采样：正文长度 / 停止按钮是否消失 / 是否出现"已停止"字样
期望：点击后停止按钮消失 + 消息进入明确终态（如"已停止生成"并保留已生成内容）
实际：
  · 停止按钮 1s 内消失（stopGone=true）
  · 正文长度 15 次采样恒为 676（不再增长）——**流确实被中断**
  · 但 15/15 次 thinking=true："深度思考中"永不结束；stoppedWord=false（无"已停止/已中断/已取消"）
  · 另一次独立复现等 30s 仍停在"深度思考中"（probe-stop/after-stop-30s.png）
  · 取消后仍可继续提问（askAfterCancelOk=true），会话未死锁
判定：FAIL —— "中断"PASS，"取消后无终态"FAIL；整条计 FAIL
影响：用户点停后看到气泡永远转圈、零反馈，无法判断"我停了"还是"它卡了"
证据：AG-3/evidence/S7-ui3/U6_cancel.json（samples 15 条逐秒）、u6-1-streaming.png、u6-2-after-cancel.png
      AG-3/evidence/probe-stop/after-stop-30s.png（30s 复现）
复跑：node AG-3/scripts/ag3_s7_ui3.js
```

### S6-1 / S6-2 / S6-3 纯向量 / 纯全文 / 混合（三模式各一次）

```
入口事实：三种模式在 UI 上**没有切换入口**——`search_policy` 1/2/3 属于助手配置
          （alg_retrieval_service/app/base.py:100；retrieval_service.py:391 search_policy_map），
          检索页只暴露关键词与助手选择。故按接口层直连检索服务 19995 实测。
公共 payload：{"query":"智造贷最高授信额度是多少","knowledge_base_name":["kb_9"],"top_k":10,
              "enabled_faq":false,"enabled_graph":false,"enabled_rerank":false,"search_policy":<1|2|3>}

混合 policy=1：http=200 code=200 docs=3 elapsed=1.33s
  top1 pk=626225001556669433 score=0.6000 st=[milvus,es,es] → R12FIX-product-intro.pptx/V1/…
  top2 pk=139363536840301567 score=0.4286 st=[milvus,es,es] → R12FIX-product-loan.docx/V1/…
  top3 pk=1095912197551331871 score=0.1111 st=[milvus]     → R12FIX-credit-ledger.xlsx/V0/…（台账）
纯全文 policy=2：http=200 code=200 docs=2 elapsed=0.10s
  top1 pk=626225001556669433 score=0.4000 st=[es,es]
  top2 pk=139363536840301567 score=0.2857 st=[es,es]
  → 台账未被词面命中（表格块靠带表头的行文本，属预期）
纯向量 policy=3：http=200 code=200 docs=3 elapsed=2.10s
  top1 pk=626225001556669433 score=0.2000 st=[milvus]
  top2 pk=139363536840301567 score=0.1429 st=[milvus]
  top3 pk=1095912197551331871 score=0.1111 st=[milvus] → 台账被向量路命中
期望：三模式均 200 且非空；混合 ⊇ 单路并集
实际：三模式均 200/非空；混合 3 条 = ES 2 条 + 向量 3 条去重（含台账），search_type 逐条可分辨
判定：PASS（3/3）
证据：AG-3/evidence/api/S6-retrieval-20261027T160318Z.json（hybrid/es_text/milvus_vector，含 summary 逐条）
复跑：ag3_api_probe.py
```

**判据自检**：只用 `search_type` 判"哪条路贡献"，不用"引用条数"当判据（去重会掩盖）。
台账在向量路出现、在全文路缺席，正好证明两路分别真的执行过，而不是同一结果贴两个标签。

### S6-4 同 query 连跑两次一致性

```
run1 pk=[626225001556669433, 139363536840301567, 1095912197551331871]
run2 pk=[626225001556669433, 139363536840301567, 1095912197551331871]
same_order=true，set_equal=true，overlap=3/3
判定：PASS
证据：同上 consistency
```

**判据自检（重要）**：第一版取的是 `metadata.pk`，该字段**不存在**（`pk` 在 doc 顶层），两组都变成
`[None,None,None]` → `same_order=True` 恒真，是**空转断言**。已改 `doc_pk()`（顶层 pk → metadata.chunk_pk → id）
后 overlap 由 1 变 3，判据现在真的在比内容。

### S6-5 无结果 query → 明确"无结果"、不得报错

```
query：zzzqqq 量子纠缠超导材料的临界温度是多少 zzzqqq
rerank 开（产品问答默认走 rerank）：
  http=200 code=200 docs=0
  msg="查询成功,但是经过重拍模型后，查询结果皆小于重拍阈值，没有符合的答案，请重新设置阈值或修改问题"
rerank 关（对照，非产品默认）：http=200 docs=4（score 0.6/0.51/0.17/0.125，全为语料内无关块）
判定：PASS（以产品默认为准：明确"没有符合的答案"，不报错、无 5xx）
证据：api/S6-retrieval-*.json（no_result.rerank_on / rerank_off）
```

`rerank 关` 那 4 条不判 FAIL：`enabled_rerank=false` 走 `no_rerank_score` 分支跳过阈值过滤
（reranker_service.py:232），属该分支既定行为；记 INFO，不并入结论。

### S6-6 表格类文件可被检索到（跨索引，§1.6）

```
query：华东精密制造的授信额度是多少
http=200 docs=3，其中表格命中 1 条：
  pk=1095912197551331871 st=[milvus] → R12FIX-credit-ledger.xlsx/V0/…
  正文首行：|客户名称|所属产业链|信用评级|授信额度(万元)|已用额度(万元)|五级分类|到期日|
判定：PASS
证据：api/S6-retrieval-*.json（table_cross_index.table_hits）
```

### S6-7 结果 pk 必须存在于当前 ES 索引

```
核验方式（写明以便复核）：
  pks = 该次检索返回的 doc 顶层 pk
  POST http://127.0.0.1:19200/{kb_9, table_chunks_kb_9, table_summary_kb_9}/_search
       {"size":N+5,"_source":false,"query":{"ids":{"values":pks}}}
  取三索引 hits._id 并集 ∩ pks
实际：3/3 命中，missing=[]
      其中 1095912197551331871 只在 table_chunks_kb_9 命中 → 表格块确实来自 table_chunks 索引（§1.6）
判定：PASS
证据：api/S6-retrieval-*.json（pk_existence: rate="3/3", verify_method 原样记录）
```

### 数值断言（授信额度）

```
基准：V1=8000 万 / V0=5000 万（kb_9 有效版本 V1）
接口层答案：8000 万元（多次一致）
UI 层答案：8000 万元（多次一致）
原文可支撑：点开引用抽屉后正文里直接看见
  "二、授信额度　单户最高授信额度为人民币 8000 万元，其中信用方式不超过 1000 万元…"
判定：PASS（数值能在引用原文里找到，不是模型自由生成）
证据：AG-3/evidence/S7-ui/u1-03-citation-open.png
```

---

## 3. 缺陷清单

P0 阻断 0 / **P1 主流程不可用 1** / P2 局部 3 / P3 体验 4

### P1-1 引用链路"表格块 → 表格文件"打开原文失败（在**本次运行包**上必现；用户看不到任何内容）

> **路径域（必须与 AG-2 的结论分开读）**：本条只针对**引用链路**——聊天页点"知识溯源"里的表格块引用。
> **详情页预览是另一条路径且正常**：`POST /file/stream` + `convertedFilePath` 可渲染出表格（AG-2 的 S5-06 / S12-01）。
> 所以不存在"同一个 xlsx 一边 PASS 一边 FAIL"的矛盾——测的不是同一条路径。
>
> 版本边界：本判定基于线上运行包（md5 `de242450…`，dist 13:22）。该包是否落后于 HEAD、以及 HEAD 是否已修此问题，
> **我未验证**（见 §0.1 + AG-2 的漂移证据）。下面判定的是**用户此刻实际遇到的行为**。

- **现象**：点"知识溯源"里的 `.xlsx` 条目，抽屉直接报 `加载失败：原文不存在或已删除（知识库文件不存在）`，无正文、无画布。
- **复现步骤**：
  1. `/chats/main` 选 `R12默认问答配置`
  2. 问 `华东精密制造的授信额度是多少？`（答 3000 万元，"知识溯源 3"）
  3. 点"知识溯源" → 点右栏 `R12FIX-credit-ledger.xlsx`
- **期望 vs 实际**：期望 `presign(key=真实对象键)=200` 并在抽屉看见台账；
  实际 `presign(key=.../V0/parsed/tables/授信台账.md)` → `404 {"errorCode":"10002","errorMsg":"知识库文件不存在"}`。
- **佐证**（同一文件三个键，我直连复核）：`.../V0/parsed/tables/授信台账.md` → **404**；
  `.../V0/parsed/R12FIX-credit-ledger.xlsx.txt` → 200；`.../V0/R12FIX-credit-ledger.xlsx` → 200。
- **归因（已修订：根因是"键构造缺 `table-N-` 序号前缀"，不是"服务端下发了不存在的路径"）**

  修订说明：本条初版写的是"服务端 `parsedFilePath` 与实际落盘不一致"，方向对但定性错——
  这么说会让修复方去查"解析是不是没产出文件"，而**解析其实产出了**，只是名字多一个序号前缀。
  该修订由 AG-2 提出对照、TL 独立复核后裁定，我又自己独立复跑了一遍键矩阵（下表，evidence 有落盘）。

  我独立复跑的键矩阵（admin token 只读，`evidence/probe-xlsx/presign-key-matrix-AG3.json`）：

```
键                                                                    presign   结论
A 详情页实际用键   .../V0/parsed/R12FIX-credit-ledger.xlsx.md           200      可用
B 引用链路失败键   .../V0/parsed/tables/授信台账.md                      404/10002 ★缺陷
C 服务端公布键     .../V0/parsed/tables/table-0-授信台账.md              200      ★存在！
D 落盘 txt        .../V0/parsed/R12FIX-credit-ledger.xlsx.txt           200      可用
E 真实对象        .../V0/R12FIX-credit-ledger.xlsx                      200      可用
```

  服务端自己在 `GET /index/knowledgeBase/file/folder/list?kbId=9` 里公布了正确键（我直连复核，http=200）：

```
R12FIX-credit-ledger.xlsx
  convertedFilePath = http://127.0.0.1:19000/r12-rag/kb_9/R12FIX-credit-ledger.xlsx/V0/parsed/R12FIX-credit-ledger.xlsx.md
  tableFilePaths    = ["http://127.0.0.1:19000/r12-rag/kb_9/R12FIX-credit-ledger.xlsx/V0/parsed/tables/table-0-授信台账.md"]
docx-table.docx
  tableFilePaths    = ["http://127.0.0.1:19000/r12-rag/kb_9/docx-table.docx/V0/parsed/tables/table-0.md"]
```

  事实链：
  ① 对象名带序号前缀：`tables/table-0-授信台账.md`（C，200）——即 `table-N-` 规则，本例 N=0；
  ② 引用链路拼的是 `tables/{tableName}.md` = `tables/授信台账.md`（B，404）——**少了 `table-N-` 序号前缀**；
  ③ 服务端已经在 `tableFilePaths` 里公布了 ①，引用链路**没有用它，而是自己又拼了一次**；
  ④ 所以不是"文件被删"、也不是"解析没产出"，是**同一条路径被两处各自拼接，规则不一致**。
  ⑤ 附带更正：`…/V0/parsed/<fileName>.md`（A）不是 `.txt`，初版写"落盘是 .txt"也不准确——
     解析产物同时有 `.md`（A）与 `.txt`（D），两者都 200；问题只在 `tables/` 这一支的命名。

- **为什么会调 presign（分支层 + 调用点，用"调用点穷举 + 排除法"收敛，不是猜）**：

  第 1 步（fileType 是什么）：该引用的文档 `type` 字段实测是 **`'table'`**（不是 `'xlsx'`），
  见 UI 实际收到的 SSE 引用载荷：`type='table' | chunk_type=table | table_name=授信台账`。

  第 2 步（穷举所有可能发 presign 的代码）：entry bundle 内 `os(`（= `getPresignedObjectUrl`）**调用点共 3 处**，
  且 `os` 没有被作为值传给其它组件（`:\s*os` / `,\s*os` / `(os` 均无匹配）：

```
① nh 图片分支     gr(s) ? { filePath: await os(...) }                    → 需 fileType ∈ 图片
② nh else 分支    (await os(...), { filePath: a, streamApiUrl: wt })     → 需 fileType ∉ office/sheet/image
③ 另一预览组件     if (gr(r)) { const _ = await os(j, ...) }              → 需 fileType ∈ 图片
```
  另：全量 874 chunk 中 `file/presign` 只命中 entry + index-legacy（2 个文件），没有第三个组件。

  第 3 步（排除）：`type='table'` ∉ 图片（①③ 排除）、∉ office/sheet（`Go` 数组是 `["xlsx","xls","csv"]`，
  **不含 `table`**）→ **只剩 ② `nh` 的 else 分支**，它必调 `os(source)` → presign。

  与观测一致：只看到 1 个 presign、没有任何 `file/stream` 调用（else 分支先 presign、抛错即止）。

  **证据等级**：这是**排除法推断（强），不是 hook 直测**。若要转成直接观测，需在浏览器里 hook `nh` 入参
  或加日志 —— 属**需他人执行**，我不改代码。AG-2 的记录件把这行保留为 UNVERIFIED，我不反对这个保守写法；
  但两种写法都不能写回"presign 是表格组件自己发的"（那是我和他先后踩过的同一坑）。

- **影响面**：所有 `chunk_type=table`（块在 `table_chunks_*`）的引用都点不开原文。
  边界要说准（采纳 AG-2 的对照）：**"整个 xlsx 预览都断"不成立**——详情页（S5）走
  `POST /file/stream` + `convertedFilePath`（A 键）能正常渲染出表格；
  **断的只是"表格块 → 表格文件"这一跳**（引用链路）。
- **稳定复现**：2/2（UI 两次各复现；B 键 404 稳定）

- **缺陷归属与修法（决定谁来修；AG-2 对照 + TL 独立复核 + 我独立复跑，三方一致）**：

```
缺陷位置在 Java 侧路径拼装（Document.java:82），不在前端 fileAccess.ts 的回退逻辑
前端回退是"照后端给的 source 再拼一次"，它忠实执行了后端给错的值

✘ 不是：文件不存在 / 解析没产出（会把修复方引去查解析产出，那条路查不出东西）
✔ 而是：键构造缺 `table-N-` 序号前缀——对象真名 tables/table-0-授信台账.md（本例 N=0），
        引用链路拼成 tables/授信台账.md；同一对象另有两种可用键且内容一致：
          V0/parsed/R12FIX-credit-ledger.xlsx.md（详情页用的）、V0/parsed/R12FIX-credit-ledger.xlsx.txt
        且系统自己已经在 folder/list.tableFilePaths 里公布了带 table-N- 的正确键，引用链路没用它
        → 缺的不是"产出"，是"引用链路没按已公布的键拼"

→ 修复建议（优先级从高到低）：
  1) 首选：引用链路直接复用服务端已公布的 tableFilePaths，不要再自己拼一次
     （再拼一次就会再错一次——这是本轮第三次"同一条路径被两处各自拼接"）
  2) 次选：Document.java:82 改为从 tableFilePaths 取值 / 或按 table-N-{tableName}.md 规则拼
  两条二选一，不要两头都改——今天已经出现过一次"两头各改一半又错一倍"
```

  TL 复核的静态证据（`rag-common/.../qa/dto/Document.java:75-88`）：

```
if (fileType in [xlsx,xls,csv]) {
    if (tableName 非空)  filePath = minioUrl + "/" + <source 目录> + "/parsed/tables/" + tableName + ".md"
    else                 filePath = minioUrl + "/" + <source 目录> + "/parsed/" + fileName  + ".md"
}
```

  即：表格块（`chunk_type=table`、`tableName=授信台账`）被拼成 `…/V0/parsed/tables/授信台账.md`（B，404），
  而实际存在的同名对象是 `…/V0/parsed/tables/table-0-授信台账.md`（C，200）。
  **拼出来的路径与真实对象名只差一个 `table-N-` 序号前缀（本例 N=0）——是拼键规则的通病，不是某一张表的个例。**

### P2-1 取消生成后无终态：气泡永久"深度思考中"

- **现象**：点停止按钮后流确实中断，但气泡永远停在"💭 深度思考中"，无"已停止"、无内容。
- **期望 vs 实际**：期望"已停止生成"终态并可继续提问；实际 15s（另一次 30s）采样 thinking 恒 true、
  stoppedWord=false，停止按钮已消失、正文长度恒 676 不再增长。
- **影响面**：用户无法区分"我取消了"与"它卡住了"；不影响再次提问（askAfterCancelOk=true）。
- **稳定复现**：2/2
- 证据：`S7-ui3/U6_cancel.json`、`probe-stop/after-stop-30s.png`

### P2-2 `/qa/feedback/que/list` 进入聊天页即 500（7 次请求全 500）

> **三方独立复现（3/3 观察者）**：AG-1 记 D-9、AG-2 记 P2-03、AG-3 记 P2-2，同一缺陷三方各自独立撞见。
> 合并报告请按一条收录并注明"三方独立复现（3/3 观察者）"。

- **现象**：`/chats/main` 加载时 `GET /proxy/qa/feedback/que/list` 全 500，控制台红字。
- **服务端原文**：`com.alibaba.fastjson2.JSONException: syntax error : {, offset 1, character {, line 1, column 1`
  `at com.gientech.ragqaservice.application.service.impl.FeedbackAppServiceImpl.queList(FeedbackAppServiceImpl.java:157)`
  → 拿 `{}`（对象）去 `JSON.parseArray`（期望数组）。
- **期望 vs 实际**：期望列表正常（或空列表 200）；实际 500，反馈列表不可用。
- **影响面**：反馈功能不可用；每次进聊天页产生 1 条 500，噪声会掩盖真故障。
- **稳定复现**：7/7（本角色 7 个 context 各 1 次）

### P2-3 跨角色发现（归属 S1/AG-1）：业务校验失败被 GlobalHandler 抛为 HTTP 500

> 归属按协调者裁决：**现象/证据归我（AG-3 实测），归因与定性归 AG-1（S1 范围）。已同步 AG-1。**

- 现象：`POST /proxy/auth/user/login` 验证码不对时返回 **500** +
  `{"success":false,"errorMsg":"验证码错误！","errorCode":"30000"}`。
- 服务端原文：`com.gientech.ragcommon.infrastructure.exception.ApplicationException: 验证码错误！`
  → `GlobalHandler` 当系统异常处理。
- 定性（引裁决语）：业务校验失败被 GlobalHandler 抛为 HTTP 500，**调用方无法区分"输错验证码"与"服务异常"**。
- 我的实测：3/3 次 UI 登录尝试均如此（`evidence/explore/login-attempts.json`：
  attempt1~3 全部 `http:500 body:{"success":false,"errorMsg":"验证码错误！","errorCode":"30000"}`）。
- 记在缺陷清单里是因为它会影响所有需要 UI 登录的角色、并会触发 §1.8 的归因陷阱；
  **S1 的 captcha 登录判定不进我的报告分母**。

### P3-1 助手配置名乱码（mojibake）

- 现象：助手标签显示 `R13 Global æµ‹è¯•åŠ©æ‰‹`、`R13 FAQ æµ‹è¯•åŠ©æ‰‹`（`æµ‹è¯•åŠ©æ‰‹` = UTF-8 被按 Latin-1 解码，原文应为"测试助手"）。
- 影响：可读性，不影响功能。稳定复现：每次加载 2/2 条。

### P3-2 会话列表时间戳两种口径混排

- 现象：同一列表既有 `10:27`，也有 `26-10-28 10:27:43`（两位年份 + 带秒）。
- 影响：像两条不同来源的数据；不影响功能。稳定复现：≥5 次截图均可见。

### P3-3 头像走 MinIO 直链被 403

- 现象：`GET /minio/dev-rag-data/header_pic/JIABINBIN00/微信图片_20231212….jpg` → 403（5 次/场景）。
- 归因：撤匿名读后头像仍用直链（应改预签名，与 `fileAccess.ts` 其它对象一致）。
- 影响：头像不显示；不影响功能。

### P3-4 文案错字 2 处

- 登录页用户名输入框 placeholder = `输入用户名字`（应为"输入用户名"）。
- 检索无结果提示 `经过重拍模型后`（应为"重排模型"）。

---

## 4. 未覆盖项

| 场景 | 原因 | 谁能解除阻塞 |
|---|---|---|
| 检索测试页（`/chats/knowledgeSearch`）的 UI 层点击 | 该页每次搜索都会由产品自己写"检索历史"（`api_kbSearchHistoryAdd`，`KnowledgeSearch/index.tsx:199`），与 R1"只读角色全程零写入"冲突；S6 五项已在检索服务接口层全量覆盖 | 无需解除。如 TL 明确"允许产生产品自身的检索历史写入"，我可在 5 分钟内补跑 |
| 纯向量/纯全文/混合的 **UI 切换** | UI 无该入口（`search_policy` 属助手配置，检索页不暴露） | 需产品加入口；当前以接口层验证替代，不算 UNVERIFIED |
| 无结果 query 的 UI 呈现 | 同上（入口只在检索测试页） | 同上 |
| 多版本 V0/V1 分别问答（S10） | 属 AG-4 范围 | 不阻塞我 |
| **图形验证码登录流程本身（S1）** | **因绕行未覆盖**：我用注入式会话（服务端签发 token 写前端存储）建立会话，未走"输验证码→校验→发 token"的完整链路；该链路判定归 S1 | 由 AG-1 单点覆盖 |
| 密保问题设置弹窗对业务的影响 | **因绕行未覆盖**：注入式会话不触发该弹窗，我无法判定它是否会拦截引用点击/历史加载等操作 | 由 AG-1 覆盖；若需我复测，请提供已登录且未设密保的会话 |

**零写入边界声明**：全程未建库、未删档、未改配置、未重启服务。但"只提问"本身会让**产品自己**写入
`qa/dialogue/create`（会话）+ `queryId`（提问记录）+ 问答历史；这是提问的必然副作用，我未做任何额外写入，
也未删除这些记录（删=写）。

---

## 5. 观察项（不判 FAIL，但 TL 需要知道）

- **O-1 我自己第一版有 2 处空转/假红，已修并留痕**：
  ① `es_all_sources()` 只读主索引 → 台账取不到有效版本 → 假红（改跨三索引）；
  ② `metadata.pk` 不存在 → 一致性断言恒真、pk 存在性 `0/0`（改 doc 顶层 `pk`）。
  写在这里是因为：不写会让报告更"好看"，但那是假的。
- **O-2 同一问题"接口层 refs=3 / UI refs=1"**：
  接口层走 `POST /qa/ai/question`（configId=1）；UI 走 `/proxy/qa/ai/question…` 且带
  `enableThinking:false`、助手配置 `R12默认问答配置`。同一文件同一问条数差 3 vs 1。
  不判 FAIL（1~3 属正常波动，答案口径一致、引用三段全绿），但**两条路径检索参数不一致**是事实，
  是否要求同口径请 TL 定。
- **O-3 引用里混入台账块**：问"智造贷最高授信额度"，接口层第 3 条引用是 `credit-ledger.xlsx`（score 0.1111）。
  答案 8000 万来自 loan.docx，台账只是词面命中"授信额度"。不判 FAIL，但记一条：低分无关引用未被过滤。
- **O-4 验证码取值的更正与最终口径（我先前结论已被推翻，此处更正留痕）**：
  **我先前写"从存储侧无法还原 4 位明文"是错的**，TL 已独立复现并裁决：
  Redis 值按 Kryo 形态取字节后，**丢首字节、其余每字节 `& 0x7f` 即明文**。
  以我自己给的样本验证：`03 35 6e 33 e5` → 丢 `03`；`35&7f='5'`、`6e&7f='n'`、`33&7f='3'`、`e5&7f=0x65='e'`
  → 明文 `5n3e`，是完整 4 位。我当时直接读原始串、没做低位掩码，把 `e5` 误当"缺位/高位字节"。
  → 因此**本条不写进缺陷清单**，也不保留"存储侧不可还原"的说法。
  仍然成立的那半条：`captcha key = MD5(来源IP+UA)`，同 (IP,UA) 反复请求**覆盖同一 key**，
  多角色并行会互相踩值。故按统一口径：并行期间一律用 `/auth/user/simpleLogin` 取**服务端签发** token，
  写 `localStorage["gitech_ril:rag_ai"]` + cookie `rag_ai_token` 建立前端会话（见 §0.2 披露）。
  验证码解码的独立证明见 `AG-1/evidence/S1/captcha-decode-proof.log`。
- **O-5 前端会话存储键**：`gitech_ril:rag_ai`（`const/index.ts:1-2` + `core/helps/appPassport.tsx:52`），
  token 取自 `data.userInfo.token`（`src/apis/token.ts`），必须在页面脚本执行前注入，否则
  `getTokenLocal()` 会立刻 `window.location.pathname="/login"`（我用 `addInitScript` 而非事后 `evaluate`）。

---

## 6. 自检

```
断言总数            22（可判断言；另有 2 条因绕行未覆盖，单列 UNVERIFIED）
已执行              22
NOT RUN             2（检索测试页 UI 层 / 无结果 query 的 UI 呈现；原因见 §4）
INFO（不判）         1（rerank 关时的无结果对照，非产品默认分支）
PASS                19
FAIL                2（S7-4 表格引用打不开 / S7-12 取消无终态）
BLOCKED             0
UNVERIFIED          2（① 图形验证码登录流程本身——因注入式绕行未覆盖，由 AG-1 单点覆盖；
                       ② 密保弹窗对业务的影响——注入式会话不触发该弹窗，无法判定）
ENV_EVENT           0（pid 开工/收工一致；前端 md5 前后一致）
是否用旧证据         否，全部为本轮（2026-10-28 00:00~10:50）新截图/新请求
是否含注入           否（无客户端拦截造故障）。
                     **注入式绕行：仅"会话建立"一项——使用服务端签发的真实 token 写入前端存储
                     localStorage["gitech_ril:rag_ai"]，未伪造 token / 未伪造接口返回 / 未改服务。**
                     密保弹窗绕行：**未使用**（注入式会话不触发该弹窗，也未提交任何密保设置）。
服务代次             8088=1403651 18082=2139785 18083=1647331 19527=1823402 19529=1461792 19995=1481869
                     （收工复核一致）
前端版本             assets/index-CpE2zvYY.js · 315576 字节 · md5 de2424501bd29e358043049876db2a75（线上=宿主）
                     ⚠ §1.4 只证"线上==宿主"，**不证 dist 由当前 HEAD 构建**；dist 13:22 < src 13:35 < r14-D 16:19（见 §0.1）
证据目录             AG-3/evidence/{api,S7-ui,S7-ui2,S7-ui3,S7-hist,
                                  probe-chat,probe-cite,probe-stop,probe-xlsx,explore}
```

**证据失效声明（避免误读同一目录里的作废件）**

- `S7-ui/U3_multiturn.json`、`S7-ui/U6_cancel.json` 是**第一批**跑出来的作废件：
  前者被上一问的"知识溯源"文案误判成"新一轮已完成"（本轮不判），后者点错了元素（点到了附件按钮）导致
  "看起来没停"。**这两份不作为任何判定依据**，S7-U3 / S7-U6 一律以 `S7-ui3/` 下的同名文件为准。
- `explore/` 目录里保留了最初的 UI 登录尝试（3 次均 500 验证码错误），是 §3 P2-3 的原始证据；
  `explore/storageState.json` 是那次失败登录的残留，未用于任何场景。

**每条 PASS 的反向自问（"如果这里其实是错的，我这个判据能发现吗？"）**

- 引用"三段全绿" → 若其实引的是 V0 旧稿，第③段会红（`/V` 前缀归一并取最大版本，不按 title 比）。
- "打开原文看得见内容" → 我不只看 `previewStream=200`，还判 `#pdfBox` 存在 + canvas 采样非空白（2500 个非透明像素）；
  若服务端回 200 但内容是空白页/错误页，这条会红。
- "表格类引用" → 我不用"接口 200"糊过去；直接抓 presign 的 key 并复核该 key 是否真存在，所以能逮住"接口机制正常、对象键错"这种假绿。
- "取消" → 我不只看停止按钮消失，而是 15 次逐秒采样正文长度与终态文案，所以能分出"流断了"和"UI 没终态"两件事。
- "一致性/pk 存在性" → 我踩过 `metadata.pk` 恒 None 的空转，改判据后 overlap 由 1→3；若判据没改，这里会是假绿。
- "无结果" → 我把 rerank 开/关两态都跑，避免用"非默认分支返回 4 条"误判成"无结果判定失效"。

**结论**：S7 主链（提问→引用→打开原文→改写→多轮→历史→连跑）在 docx/pptx 类文件上全程可用；
**引用链路里"表格块 → 表格文件"这一跳是硬断点（P1）**，且它是引用可回指三段里第②段的真实红灯，不是环境问题。
（路径域限定：详情页预览 xlsx 是另一条路径且正常——`stream` + `convertedFilePath`，见 AG-2 的 S5-06 / S12-01；
不存在"同一个 xlsx 一边 PASS 一边 FAIL"的矛盾。）
S6 三条检索路、一致性、无结果、跨索引、pk 存在性全部实测通过。

**三条口径的最终落点（与协调者裁决对齐）**

1. 验证码：我先前"存储侧不可还原"的判断**已被推翻并更正**（Kryo 首字节丢弃 + 其余字节 `& 0x7f`，
   样本 `03 35 6e 33 e5` → `5n3e`）。该结论未进缺陷清单，也不作为任何判据。
2. 会话建立：统一走 `/auth/user/simpleLogin` 服务端签发 token（并行期 key 会互相覆盖，这是唯一确定性方式），
   已在 §0.2 与 §6 显式披露；由此未覆盖的 2 条断言标 UNVERIFIED，**不用 API 层结果冒充 UI 层 PASS**。
3. 版本漂移：§1.4 md5 只证"线上==宿主"。我把所有**以 HTTP/页面事实为准**的判定与**以源码推断**的归因分开，
   P1-1 的归因改为"bundle 内无 `parsed/tables` 字面量（可 grep 复核）+ Java 侧生成该路径"，
   不再依赖可能未构建进包的 `fileAccess.ts`。

---

## 7. 判据演进（供合并报告引用；TL 已要求收录）

这两条不是产品缺陷，是**我自己的判据从"会骗人"改成"会叫"的过程**。写在报告里的理由是：
合并报告如果只留"PASS 19 / FAIL 2"，下一个人会重复踩同样的坑，并且会以为那些 PASS 从一开始就是真的。

### E-1 只读主索引 → 台账版本假红

```
判据 v1：effective_version 只从 kb_9 主索引取 source→version
后果  ：台账块的 source 只存在于 table_chunks_kb_9 / table_summary_kb_9，
        主索引里查不到 → 有效版本返回 -1 → ref2 被判 version_ok=False（假红）
现象  ：S7-1 第一轮输出 "ref2 ... ver=V0/None vok=False all=False"
修正  ：es_all_sources() 改跨 {kb_9, table_chunks_kb_9, table_summary_kb_9} 三索引（§1.6）
结果  ：ref2 → ver=V0/有效V0 → all_green=True；3/3 全绿
教训  ：只查主索引不是"更严格"，是"把表格引用一律判悬空"——这是 §1.6 警告的假红镜像
```

### E-2 `metadata.pk` 不存在 → 一致性断言恒真（恒真断言比失败断言更危险）

```
判据 v1：一致性取 d.metadata.pk；pk 存在性也取 metadata.pk
事实  ：该字段在检索返回里**不存在**——`pk` 在 doc 顶层，`chunk_pk` 才在 metadata 里
后果  ：两组都是 [None, None, None]
        → same_order = (ka == kb) 恒为 True（拿不存在的字段做判据，永远相等）
        → pk 存在性 = 0/0，分母为 0，rate 看上去"没失败"
现象  ：第一轮输出 "same_order=True" 同时 "3/3 存在" 变成 "0/0"，overlap=1
修正  ：doc_pk() = 顶层 pk → metadata.chunk_pk → metadata.id 兜底
结果  ：overlap 由 1 → 3；pk 存在性 0/0 → 3/3；一致性断言现在真的在比内容
教训  ：**一个恒真的断言比一个失败的断言更危险，因为它永远不会叫。**
        判据里出现"取不到的字段"时，必须让它在缺失时 FAIL，而不是退化成 `None == None`
```

这两条的原始证据都在本轮文件里可查：`evidence/api/S6-retrieval-20261027T155947Z.json`（修正前）
与 `…20261027T160318Z.json`（修正后）、`evidence/api/S7-chat-20261027T155947Z.json` 与 `…T160318Z.json`。

### E-3（归因演进）跨角色对照推翻了我自己的根因定性

```
定性 v1：服务端 parsedFilePath 的"生成口径"与"实际落盘口径"不一致（.md vs .txt、tables/ vs 文件名）
问题  ：方向对、定性错。这个说法会让修复方去查"解析是不是没产出文件"——但解析是产出的。
        它把"两处各自拼键"的问题，说成了"产出与描述不一致"的问题，修复责任会被推给解析侧。
触发  ：AG-2 做了对照实验（详情页 xlsx 预览走 stream + convertedFilePath，能正常渲染 7列×4行），
        并给出四键矩阵，指出"对象名带 `table-N-` 序号前缀（本例 N=0）、链路拼的少了它"；
        TL 直接查 folder/list.tableFilePaths 独立复核，裁定我改；
        我又用 admin token 独立复跑五键矩阵，结果与 AG-2 完全一致（B=404，C=200）。
定性 v2：键构造不一致——对象真名 tables/table-0-授信台账.md，链路拼 tables/授信台账.md，缺 table-N- 前缀；
        且系统已在 folder/list.tableFilePaths 公布正确键，链路没有复用而是又拼了一次。
判据  ：同一对象"系统自己公布的键"与"链路实际请求的键"必须逐字符比对；
        两者不一致时，缺陷属于"拼接方"而不是"产出方"。
教训  ：① 我的归因当时只有"我这一个视角"——我看到了 404 就推"后端给错值"，
          没去问"系统里有没有一个正确值存在"。**有对照角色的环境里，单方归因不可信。**
        ② "口径不一致"是描述，"谁拼错了"才是归因；前者不能直接交给修复方。
```

E-3 的证据：`AG-3/evidence/probe-xlsx/presign-key-matrix-AG3.json`（我的五键矩阵）、
`AG-2/evidence/presign-xlsx-key-matrix.json`（AG-2 的对照）、
`GET /index/knowledgeBase/file/folder/list?kbId=9` 的 `tableFilePaths` 原文（已抄在 P1-1）。
