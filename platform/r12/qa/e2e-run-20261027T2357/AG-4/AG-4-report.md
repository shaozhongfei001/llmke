# AG-4 验收报告：global 问答 / 多版本 V0-V1 / 图谱

- 批次：`e2e-run-20261027T2357`
- 角色：AG-4（global / 多版本 / 图谱）
- 执行窗口：2026-10-27 23:58 ~ 2026-10-28 02:30（本机时区 +08:00）
- 被测对象：kb_9（前端显示名「R12验收主链」，DB `knowledge_base.id=9`）
- 结论：**S8 FAIL / S10 FAIL / S11 FAIL**，缺陷 **11 条（P0 2=AG4-01·AG4-11 / P1 2 / P2 3 / P3 4）**
- 纪律自检：全程零写入（未建库/未删档/未重启/未改库/未改配置/未提交任何弹窗设置）；证据与脚本仅落 `AG-4/`；kb_22 等他人夹具未触碰

---

## 0. 环境与版本自证（§1.4）

| 项 | 取值 |
|---|---|
| 前端 entry | `assets/index-CpE2zvYY.js`（取自 `frontend/plateform/dist/index.html`） |
| HTTP 实际字节 md5 | `de2424501bd29e358043049876db2a75`（315576 B） |
| dist 文件 md5 | `de2424501bd29e358043049876db2a75` |
| 比对结果 | **一致 → 服务端正在提供的前端 = 本仓 dist** |
| 服务代次 | 8088=1403651 / 18082=2139785 / 18083=1647331 / 19527=1823402 / 19529=1461792 / 19995=1481869（全程未变） |

锚点：`evidence/S0-version-selfproof.md`

### 0.1 绕行声明（必读，按协调者广播 §4 口径）

| 项 | 本角色处置 | 声明 |
|---|---|---|
| 会话建立 | `POST /auth/user/simpleLogin`（服务端既有同一密码校验链）取 token，注入前端 localStorage `gitech_ril:rag_ai` | **注入式绕行**：未走 UI 登录表单、未使用验证码；登录用例本身归 AG-1，本角色不对登录判定 |
| 密保问题强制弹窗 | **未出现**（因为未走 UI 登录流程，前端未触发该弹窗） | 未使用"移除遮罩"绕行；未点任何「确定/保存」，未提交任何密保设置 |
| 验证码 | 未使用 | 未关闭/未降级服务端校验 |
| 因绕行而未覆盖的断言 | 见第 4 节（其中"S8 点击引用展开原文"标 UNVERIFIED） | **不记 PASS** |

### 0.2 版本漂移声明（AG-2 已证，本报告据此自查）

- §1.4 的 md5 自证只证明「宿主 dist == 服务端下发」，**不证明 dist 由当前 HEAD 构建**（AG-2 证据：dist 构建 13:22，`src/core/components/StreamReader.tsx` 13:35 改，r14-D 提交 16:19）。
- 因此本报告所有判定**只取线上实际行为**（请求体、SSE 原文、页面文本、ES/MySQL 存储事实），不照 r14-D 的"已修复期望值"写。
- **边界（TL 更正后口径，必读）**：所谓"包落后 HEAD"**仅指 13:34 / 13:35 那两处改动**（`core/components/StreamReader.tsx` 等），**不等于 r14-D 整批未生效**。`globalMode` 注入补丁早于 13:22 就在包内，所以"开关能用"与"presign 未进包"并不矛盾——两者分别落在不同的改动批次上。
- 逐项自查结论：
  - **S8 开关判据不受影响**：`globalMode` 注入补丁在服务端下发包内实测生效（浏览器请求体出现 `"globalMode":true`，关时缺省），属实测而非 src 推断。
  - **S10 版本判定不受影响**：判据是线上整页文本 `V[0-9]` 命中 0 次 + 展开子表无版本标识；报告中引用的 `VersionDetail.tsx:603-609` 注释块**仅作辅助说明**，不作判定依据。
  - **S8「点击引用打开原文」**（ROUND-A 补充观测已完成，§2.6）：**渲染=可验 PASS**（能打开、能渲染）；抽屉身份已定死为 **DrawerPreview**（`#pdfBox`）；**`.docx` 源 presign 0 次命中，与包内实现一致**——包内 `nh` 的 **office/sheet 分支在 presign 之前就 return**（**设计分流**，非"整个函数没有 presign"）；另有一层：HEAD 里"所有类型先 presign"的 FIX-04 是 13:34:50 的改动、**不在 13:22 的包内**（重建后行为会变）。两层都不构成缺陷；失败三态文案 UNVERIFIED（未触发）。

> 观察：token TTL 很短，连续批量调用中曾出现 `401 / errorCode=30013 登录失效已过`（见 `evidence/C-sse-summary.json` 的 `off3`）。非产品缺陷，但脚本必须按批重取 token。

---

## 1. 总表

| 场景 | 子项 | 判定 | 可复核锚点 |
|---|---|---|---|
| **S8** | 开关→请求体注入 globalMode | **PASS** | ON：`…,"enableWebsearch":false,"globalMode":true}`；OFF：无 globalMode。UI 实际端点=`/qa/ai/question_re`（CDP 抓包），API 直连=`/qa/ai/question`，两者都按开关正确注入。`evidence/S8-result.json`、`D-ui-request-body.json` |
| S8 | UI 实际链路终态（`question_re` + global 开） | **FAIL**（缺陷 AG4-11 = **P0**） | 3/3 终态 `status=3`、refs=0、末帧「模型暂无法返回，请稍后再试!!!」；同端点关模式 3/3 正常。代码级：`publicQuestionRe()` 无 global 分支（§2.8）。`evidence/E-re-frames-summary.json` |
| S8 | 失败前已提交不可撤回内容（独立后果 R1） | **FAIL** | 帧 1~14 正常吐「…5000万元。」，帧 15 才 `status=3` 报错 → 错误答案先于错误提示到达用户，UI 不撤回已渲染内容（3/3）。见 §2.7 |
| S8 | UI=5000万 与 API=1000万 的归属 | **两条链路（非同一接口抖动）** | UI 走 `question_re`、API 直连走 `question`；`AiController` 接口文档写明二者差别是"返回接口拼接 / 返回结果未拼接"，且 global 只在 `question` 实现。四格对照 `evidence/D-endpoint-compare.json`，结论 §2.5(d)、§2.8 |
| S8 | 开关→UI 视觉态 | PASS | localStorage `r13_global_mode` 1↔0；「GraphRAG 全局」角标 出现↔消失。`evidence/S8-01-global-on-flag.png`、`S8-03-global-off-flag.png` |
| S8 | 开=社区聚合 / 关=块级（区分判据） | PASS（判据=社区标记，非"跨文档"） | 开：答案含 `[L0-18625408]`、`search_type=["graph_community"]`；关：无社区标记、refs 为块级 source。`evidence/B1-global-G1-3runs.json`、`C-on-1.sse.txt` |
| S8 | 每条结论回链三段（①形态②传输③版本） | **FAIL** | ②传输绿（服务端 presign 200 + fetch 200 字节）；①形态绿；**③语义断**：3 条结论统一引 `L0-18625408`，该社区正文不含任何评级/加点（`evidence/C-community-index-raw.json`） |
| S8 | 引用"展开原文"渲染 | **PASS（可验）** | 点「知识溯源」→ 点条目：`previewStream` 200、抽屉标题 `R12FIX-product-loan.docx 1/1 111%`、`canvas=1` 实渲染。`evidence/S8-ref3-result.json`、`S8-ref3-02-after-click.png` |
| S8 | 引用路径 presign 前置校验 | **已验（非缺陷：按类型分流）** | 抽屉=**DrawerPreview**（`#pdfBox`）；`.docx` 源 `presign` **0 次**，与包内 `nh` 的 office 分支一致（office/sheet 在 presign 前 return）；HEAD 源码的"所有类型先 presign"是 13:34 改动、不在 13:22 包内。见 §2.6(c)(d) |
| S8 | 引用路径 失败文案三态 | **UNVERIFIED（有证据）** | 该路径不发 presign → 三态文案不会出现；三态代码在 entry chunk 内存在，属"未触发"而非"未实现"。见 §2.6(d) |
| S8 | 数值可支撑率 | **FAIL** | global 1/3（30 支撑；60×2 在被引原文中不存在）；local 2/2。`evidence/B6-number-support.json` |
| S8 | 拒答不得编造数值 | PASS | 海川题：开=`事实中未提及 [L0-3c882b30]`；关=「并未明确说明…建议咨询」，两侧均无编造比例。`evidence/B4-refusal.json` |
| S8 | 同题连跑 3 次 refs 波动 | PASS（稳定） | global 开 1/1/1；local 关 3/3/3。`evidence/B1`、`B2-amount-onoff-3x.json` |
| S8 | 假拒答识别（§1.7） | **FAIL**（缺陷 AG4-10，独立条目） | 「智造贷的授信额度是多少？」global 开 **3/3** 返回「事实中未提及」，但该事实在库（ES `kb_9` 有 V0/V1 两块额度事实）且所引社区正文含「最高额度 5000万元」→ 非 ENV_EVENT（同批 G1 加点题 3/3 正常作答 30/60/60）。`evidence/A3-global-3runs.json` |
| **S10** | 版本管理入口可达 | PASS | Tab「版本管理」存在可点：`知识解析/FAQ/配置/检索测试` + `文件管理/版本管理/图谱增强`。`evidence/S10-01-version-tab.png` |
| S10 | V0/V1 切换控件 | **FAIL（历史缺口仍在）** | 面板 36 个控件、整页文本 `V[0-9]` 命中 **0** 次；「版本号」列已注释（源码 `VersionDetail.tsx:603-609`）；展开分组后子表只有两行文件名，无版本标识。`evidence/S10-04-version-group-expanded.png`、`S10-expand-result.json` |
| S10 | 默认应答取 V1 | **PASS** | 「智造贷最优/最高额度」local **3/3** = 8000万元，引用 `…/R12FIX-product-loan.docx/V1/…`、`…/R12FIX-product-intro.pptx/V1/…`。`evidence/B2-amount-onoff-3x.json` |
| S10 | 分别问 V0 / V1，V0 引用必须指 V0 | **BLOCKED**（不可达） | 无版本入口，无法在界面选择 V0；显式在问题里点名 V0 仍返回 8000万 + V1 引用，V0 内容（5000万）问答链路不可达。`evidence/B3-ask-version-explicit.json` |
| **S11** | 图谱页是否有实体/关系 | **FAIL** | 「图谱增强」列表恒「暂无数据」(`total=0`)；「可视化图谱」渲染出画布但 **节点数 0/0、关系数 0/0**。`evidence/S11-01-graph-tab.png`、`S11-02-visual-allgraph.png` |
| S11 | 图数据是否存在（区分"无数据"与"取不到"） | 存在 | 直连 19529 `query_graph_data` → `code=200`，2~3 条块，`provenance_quality=exact_chunk`，`identity_violations_count=0`。`evidence/C-graph-query-graphdata.json` |
| S11 | 实体追溯 | **FAIL**（页面侧不可达） | 页面无节点可点；`/graph/info/nodes`、`/graph/info/edges`、`/graph/graphStatistics/getWholeGraphStatistics` 对 admin 全返回 `401 / errorCode=30021 没有足够的权限`。`evidence/S11-network.json` |
| S11 | local 多跳 | **FAIL（未观测到增量）** | 3 个多跳题 graph_on/off 返回同一组文档：`only_on=0`（source 与内容指纹双口径）。`evidence/B8-graph-only-on.json` |
| S11 | 开/关图对照 only_on | **未观测到增量** | 同上；仅观测到 `search_type` 多出 `graph` 标记（3/0、2/0、0/0），refs 条数与来源不变。**不构成"图有效"的证据** |
| S11 | 图块可回指原文（存储事实判定） | PASS | `chunk_pk ∩ ES._id = 3/3`；块版本为 V1（有效版本）与 ledger 的 V0（唯一版本）。`evidence/B9-graph-provenance.json` |

---

## 2. 逐项证据

### 2.1 S8 global

**(1) 开关注入（双向）**
浏览器实测请求体（同题 G1，同一 sessionId）：

```
ON : {…,"configId":"1","content":"…","enableThinking":false,"enableWebsearch":false,"globalMode":true}
OFF: {…,"configId":"1","content":"…","enableThinking":false,"enableWebsearch":false}
```
对应 localStorage `r13_global_mode` = `1` / `0`，角标「GraphRAG 全局」出现 / 消失（`S8-01`、`S8-03` 截图）。

**(2) 区分判据的自我校验（§1.6）**
任务书写「开时答案跨文档、关时不跨」。实测**不能**用"引用条数"当判据：开=1 条、关=3 条，方向相反。逐题核对后确认真正可判的差异是**答案是否由社区摘要 map-reduce 产出**：
- 开：答案带社区标记 `[L0-18625408]`，引用对象 `title=社区摘要 L0-18625408`、`search_type=["graph_community"]`（`C-on-1.sse.txt`）；
- 关：无社区标记，引用对象为块级 source（ledger/intro/loan 三份）。
因此本项以"社区标记 + graph_community"为判据判 PASS，并显式声明"跨文档"口径不成立。

**(3) 回链三段（逐步）**
| 段 | 判据 | 结果 |
|---|---|---|
| ① 形态 | source 无重复 host、无 scheme 泄漏、以 `r12-rag/kb_9/…` 开头 | 绿（3/3） |
| ② 传输 | `GET /index/knowledgeBase/file/presign?key=…` 200 且地址可取回字节 | 绿：29388 / 37543 / 5340 B，魔数 `PK\x03\x04` |
| ③ 版本 | 按 source 的 `/Vn/` **之前前缀归一**后判定版本 | 引用均指向 `/V1/`（有效版本）；ledger 无 V1，`/V0/` 即其唯一版本 |

> 版本比对一律用**前缀归一**：`r12-rag/kb_9/R12FIX-product-loan.docx` 在 V0/V1 两个 source 中相同 → 同一文档族；`title`（`…(1).docx`）+`fileName` 差异只是展示层，未参与判定。

**(4) 回链"语义段"断裂（FAIL 的核心）**
global 对 G1 的回答三条结论全部标注 `[L0-18625408]`，而该社区正文（`evidence/C-community-index-raw.json`）为：

```
- 智造贷 -面向-> 制造业中小微企业
- 智造贷 -最高额度-> 人民币5000万元
- 智造贷 -最长期限-> 三年
- 智造贷 -审批流程-> 十个工作日内完成审批
```
正文不含「江南装备 / 华东精密 / 北方重工 / AAA / AA / 60个基点」中的任何一项；真正的评级支撑社区是 `L0-3af0d4bc`（江南装备 AAA）与 `L0-60d6fa91`（两家 AA），**未被引用**。即：三段中的第③段之前还缺一段——"引用内容是否支撑该条结论"，此处 3/3 不成立。

**(5) 数值可支撑率**
| 答案 | 数值 | 被引原文可得 | 结论 |
|---|---|---|---|
| global G1 | 30 基点 | ✓（intro V1：`加点30~100BP`） | 支撑 |
| global G1 | 60 基点 ×2 | ✗（intro V1 无 60；支撑该值的 community 正文也无 60） | 不可支撑 |
| local 额度 | 8000 万元 | ✓ | 支撑 |
| local 额度 | 1000 万元 | ✓（信用方式上限） | 支撑 |

**(6) 假拒答（§1.7 的 ENV_EVENT / FAIL 区分）**
- 「智造贷的授信额度是多少？」global 开 3/3 =「事实中未提及 [L0-18625408]」。
- 同批对照：G1 加点题 3/3 正常作答（30/60/60，带社区标记）；`community_summary_kb_9` 7 条社区全部在线、`query_community` 直调正常返回 `code=200`。
- 因此**不属于**"同批全类别无来源拒答"的 ENV_EVENT 形态，判 **FAIL（假拒答）**：库内有该事实、所引社区正文也写有「最高额度 5000万元」，却答"事实中未提及"。

### 2.2 S10 多版本

- 版本分组接口确实存在多版本：`R12FIX-product-loan.docx` → `290/V0`、`328/V1`；`R12FIX-product-intro.pptx` → `330/V0`、`343/V1`（`evidence/S10-expand-result.json`、`A1-version-groups.json`）。
- 前端把「版本号」列整列注释掉（`VersionDetail.tsx` 第 603-609 行仍以注释块保留），展开分组后子表只显示两行文件名：
  `R12FIX-product-loan(1).docx` / `R12FIX-product-loan.docx`，无 V0/V1 标识，无切换控件，无"S10 版本选择"入口。
- 默认应答取 V1：local 3/3 = 8000万元（有效版本值），引用全部落 `/V1/`。
- V0 不可达：显式提问「V0 版本里…」仍返回 8000万元 + V1 引用（`B3-ask-version-explicit.json`），系统无路径取 V0 内容。
- 附加观察：`R12FIX-product-intro.pptx` 分组在当前列表未展开（`caret_n=2`，只展开了第一组），非缺陷，仅为取证范围说明。

### 2.3 S11 图谱

- 「图谱增强」列表：`GET /index/knowledgeBase/file/folder/list?fileListType=3&kbId=9` → `{"records":[],"total":0}`，页面「暂无数据」。
- 存储事实核对：kb_9 现存文件 10 个（`status=3` 解析成功），**`graph_parse_status` 全部为 1（未解析）**，其中 `docx-plain.docx` 为 4（解析失败）。即"列表为空"与"没有图谱解析成功的文件"一致，不能判为"查询失败"。
- 但「可视化图谱」页拿到的是权限错误而非空数据：三个图接口对 admin 全 401/30021；页面只表现为 `节点数 0/0 关系数 0/0`，**不提示无权限**。
- 底层图数据是有的：19529 直连 `query_graph_data`（`space_name=kb_9`）返回 2~3 条块，`provenance_quality=exact_chunk`、`identity_violations_count=0`、`chunk_pk` 与当前 ES `_id` 3/3 命中。→ 结论应写作"**前端图接口不可用（权限/网关侧）**"，而不是"该库无图数据"。
- 开/关图对照（检索层）：3 个多跳题，graph_on 与 graph_off 的文档集合按 `source` 与内容指纹双口径完全相同，`only_on = 0`。仅 `search_type` 数组多出 `graph`。按纪律记"**未观测到增量**"。

**为什么 S11 的三条 FAIL 与"图块可回指原文 PASS"并不矛盾（显式说明，避免被读成自相矛盾）**

| 层 | 观测 | 判定 | 说明 |
|---|---|---|---|
| 存储/检索服务层（19529 直连、19995 检索） | `query_graph_data` 返回 2~3 条块、`provenance_quality=exact_chunk`、`chunk_pk ∩ ES._id = 3/3`、块版本=V1 | **PASS** | 图**能**取到块，且块能回指当前 ES 的原文，代次新鲜 |
| 展示层（KB 详情 → 图谱增强 / 可视化图谱） | 列表 `total=0`；可视化 `节点数 0/0 关系数 0/0` | **FAIL** | 用户在图谱页看不到任何实体/关系 |
| 展示层（实体追溯） | `/graph/info/nodes`、`/graph/info/edges`、`/graph/graphStatistics/*` 对 admin 全 `401/30021` | **FAIL** | 是**权限/网关**问题，不是"没有图数据"——底层明明有数据 |
| 检索效果层（开/关图对照） | 3 个多跳题 `only_on=0` | **FAIL（未观测到增量）** | 图参与了（`search_type` 带 graph 标记）但没带来任何新文档，不能算"图有效" |

一句话：**"块能取到"（服务层通）与"页面看不到 / 追溯 401 / 多跳无增量"（展示层与效果层不通）是三件不同的事**，前者 PASS 不构成对后三者 FAIL 的反证；反过来，后三者 FAIL 也不否定存储层数据是新鲜的。
另外两层各有一条独立缺陷：展示层→AG4-04（401）；效果层→见 §1 总表 S11「local 多跳」行（only_on=0，未观测到增量）。

### 2.4 版本代次与数值外泄：三项补充（TL 指定，用于定级）

问题原文：**「智造贷单户最高授信额度是多少？」**，同一 configId=1，各跑 3 次。

**① 用户可见答案原文（global 开）**

```
run1/2/3（3/3 完全一致，frames=1、耗时 2.0~2.6s、http=200 status=2）：
智造贷单户最高授信额度是人民币5000万元。[L0-18625408]
引用：r12-rag/kb_9/R12FIX-product-intro.pptx/V1/R12FIX-product-intro(1).pptx
```
→ **答案给出 5000 万元 = V0 代次数值；有效版本 V1 = 8000 万元。用户拿到的是错误数值。**
→ 且引用指向 `/V1/` 原文，而该文件写的是「最高额度：8000万元」——**答案与被引原文自相矛盾**，用户点开引用即可发现对不上。

**② local（chunk 级）同题对照**

```
run1/2/3（3/3 完全一致，frames=17、耗时 13.8~19.5s）：
智造贷单户最高授信额度为人民币8000万元。
引用：…/R12FIX-product-loan.docx/V1/…、…/R12FIX-product-intro.pptx/V1/…、…/R12FIX-credit-ledger.xlsx/V0/…
```
→ 两个数（5000 万 vs 8000 万）不一致本身即证据：同一问题、同一知识库，仅因开关不同就给出相差 3000 万元的额度。

**③ 时间线：摘要是否旧代次（并列 create_time）**

| 对象 | create_time | 说明 |
|---|---|---|
| 社区摘要 L0-3c882b30 | 2026-10-27 11:06:35 | 7 条摘要中最早 |
| 社区摘要 L0-18625408 | 2026-10-27 11:06:39 | 承载「最高额度 5000万元」 |
| 社区摘要 L0-3af0d4bc / L0-60d6fa91 | 11:06:42 / 11:06:44 | 承载企业评级 |
| 社区摘要 L0-a5a28a99 / L1-bae29a49 | 11:06:46 / 11:06:49 | `update_time` 全部 = 11:06:49.95（同一批写入） |
| ES chunk loan **V0**（fid=290） | **2026-10-27 13:25:49** | 当前 chunk 代次 |
| ES chunk loan **V1**（fid=328） | **2026-10-27 13:25:55** | 比摘要晚 **2 小时 19 分** |
| ES chunk intro V0（fid=330） / **V1**（fid=343） | 13:26:13 / **13:26:53** | 同上 |

→ 摘要代次（11:06）**早于**当前 V0/V1 chunk 代次（13:25~13:26），因此"摘要不可能包含 V1 的 8000 万"是**结构性的**，不是"摘要更新过但内容写错"。
→ 佐证：AG-2 与 TL 独立核对一致——`community_summary_kb_9` 共 7 条，含"5000万"2 条（L0-18625408、L1-bae29a49），含"8000万"**0 条**。

**定级建议**：按 TL 口径①，答案给出 5000 万 → 用户拿到错误数值 → 落入 P0/P1 区间；因"数值错误 + 与被引原文矛盾 + 3/3 稳定复现 + 银行授信额度口径"，本报告定为 **P0**（如 TL 认为需再降级，可改 P1，事实与证据不变）。

### 2.5 UI 实际请求与响应逐帧：为什么 UI 是 5000万、API 是 1000万（TL 指定第 3 项）

用 CDP `Network.requestWillBeSent` + `Network.getResponseBody` **只读**观测（未拦截、未改写、未阻塞网络）。

**(a) UI 真实请求体**

```
POST http://127.0.0.1:18088/proxy/qa/ai/question_re      ← 注意端点：question_re
{"configId":"1","content":"智造贷最高额度是多少？","fileUids":[],"lastDate":1793154582931,
 "name":"智造贷最高额度是多少？","queryId":"query-ce6f39138760b8155ab37b1e1a26b165",
 "sessionId":"c5a904ce6f39138760b8155ab37b1e1a","type":"text","audioUrl":"",
 "enableThinking":false,"enableWebsearch":false,"globalMode":true}
```
- 带 `globalMode:true` ✔；`configId:"1"`（**字符串**）；`sessionId` 为 32 位 hex；端点 `/qa/ai/question_re`。

**(b) UI 响应逐帧（同题，global 开）**

```
frames=15  statuses=[1,1,…,1,3]  → 终态 status=3（错误）  refs 帧=0
失败前累计内容：智造贷的最高额度为人民币5000万元。
最后一帧内容  ：模型暂无法返回，请稍后再试!!!
```
→ UI 看到的「5000万元 + 错误提示」= **流式吐出旧代次半句 → 最后一帧转错误终态**，UI 保留已渲染内容不撤回。

**(c) 两条链路对照（同一问题，各 3 次）**

| 链路 | 端点 | globalMode | frames | 终态 | refs | 答案 |
|---|---|---|---|---|---|---|
| **UI** | `/qa/ai/question_re` | true | 15 ×3 | **3（错误）** | 0 | 「…5000万元。」→「模型暂无法返回」 |
| UI | `/qa/ai/question_re` | false | 48 | 2 | 1 | 「最高授信额度为8000万元…」✔ |
| **API** | `/qa/ai/question` | true | **1** ×3 | 2 | 1 | 「智造贷最高额度是1000万元 [L0-18625408]」 |
| API | `/qa/ai/question` | false | 39 | 2 | 3 | 「最高额度为8000万元…」✔ |

**(d) 归属结论（回答 TL 的二选一）**

**是"参数不同"：两个端点不是同一条链路**，因此 5000万 vs 1000万 的差异**不是同一接口的非确定性**，而是两条链路各自的缺陷：

| 链路 | 病灶 | 性质 |
|---|---|---|
| `/qa/ai/question`（单帧直答） | 从社区事实里取「人民币1000万元 -信用方式上限-> 智造贷」当作「最高额度」，单帧返回、不经生成 | **取错事实**（选错三元组） |
| `/qa/ai/question_re`（生成链路，UI 用户实际走的） | global 开 **3/3 终态 status=3**、refs=0；且失败前已把旧代次 5000万 流给用户 | **生成失败 + 失败时泄漏旧值** |

复现命令与证据：`probe_re_frames.py` → `evidence/E-re-on-{1,2,3}.sse.txt`、`E-re-frames-summary.json`；
端点对照：`evidence/D-endpoint-compare.json`；UI 请求体与逐帧：`evidence/D-ui-request-body.json`。

> 附带纠正一处我方表述：此前我把"UI 3/3 = 5000万 + 错误态"与"API 3/3 = 1000万"并列描述，容易被读成"同一接口抖动"。实测是**不同端点**，已在缺陷条目中按两条链路拆分（AG4-01 取错事实 / AG4-11 生成失败）。

### 2.6 引用"展开原文"路径实测（ROUND-A 补充观测：抽屉身份已定死；结论=按类型分流的正常行为，非缺陷）

> **本节有两处更正记录，都保留以便追溯：**
> ① 上一版把路径归因为 Content 抽屉 → **错**，实测是 **DrawerPreview**（证据见 (a)）。
> ② 上一版据此记了 AG4-12 "代码要调、实际没调"（P1）→ **该条已撤回**。撤回原因有两层，见 (c)(d)：
>    包内 `nh` 对 office/sheet **在 presign 之前就 return**（本就不该调）；HEAD 源码虽改成"所有类型先 presign"，
>    但那是 13:34 的改动、**不在 13:22 构建的包里**。

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

#### (c) 机制定论：包内实现是"按类型分流"，Office 分支在 presign 之前就 return

**决定性证据来自线上 bundle（AG-2 从 `index-CpE2zvYY.js` 抠出，压缩名 `nh` = `resolvePreviewTarget`）**：

```js
nh = async ({source:t, fileType:s, token:r}) => {
  const a = It(t); if (!a) throw new Error("缺少原文对象键，无法打开原文");
  return (xs(s) || Go(s))                                   // office(docx/pptx) 或 sheet(xlsx/csv)
      ? { filePath: a, streamApiUrl: ns }                   // ← previewStream，直接 return，**不调 presign**
      : gr(s)                                               // image
        ? { filePath: await os(t, r), streamApiUrl: wt }    // ← presign
        : (await os(t, r), { filePath: a, streamApiUrl: wt }); // ← 其它(pdf/txt/md) 先 presign
};
// ns = previewStream, wt = stream, os = getPresignedObjectUrl
```

本次输入 `source=…/R12FIX-product-loan.docx/V1/…`、`fileType=docx` → **命中第一分支（office）→ 本就不该发 presign**。
⇒ `hits = 0` 属于**设计分流**，不是"该调没调"，**不是缺陷**。

**交叉证据（AG-3 实测，本报告采信）：同一路径在不同 `fileType` 下结论相反**

AG-3 观测到表格块引用的载荷是 **`type='table'`**（`chunk_type=table`，`table_name=授信台账`）。而 `Go = ["xlsx","xls","csv"]` **不含 `table`** → 不命中 office/sheet 短路 →
落 `nh` 的 **else 分支** → **必然调 presign**。

于是两条观测都成立、且互不矛盾：

| 引用对象的 `fileType` | 命中分支 | presign | 观测者 |
|---|---|---|---|
| `docx`（office） | 第 1 支（office/sheet） | **不调** | AG-4（hits=0） |
| `table` / `pdf` / `txt` / `md` | 第 3 支（else） | **会调** | AG-3（表格块引用） |
| 图片类型 | 第 2 支（image） | **会调** | 包内代码（本轮未单独观测） |

**因此"预览抽屉调不调 presign"这个问法本身不完整** —— 必须带**类型域**：
同一个抽屉，`docx` 与 `table` 的结论相反。这也是本报告不再使用"该路径不调 presign"这种整体表述的原因。

**为什么"HEAD 源码"会给出相反的直觉（这是本次误判的根因，留档）**

| 对象 | presign 位置 | 时间 / 出处 |
|---|---|---|
| HEAD 源码 `core/helps/fileAccess.ts:96-108`（第 101 行） | **无条件**先 `await getPresignedObjectUrl(...)`，再按类型分支 | mtime **13:34:50**；commit `4415ed3`（16:19 `fix(r14-D)`，`git log -S "所有类型"` 命中） |
| 线上 entry `index-CpE2zvYY.js`（`nh`） | **office/sheet 分支先 return**，只有 image 与"其它"两支调 presign | dist **13:22:11**（早于上述改动 **12 分 39 秒**） |

即：线上是**中间版本**（按类型分流），HEAD 是**新版本**（所有类型先 presign，且注释写明理由：让 presign 的错误口径可区分）。
**两者都不是"矛盾"**，只是版本不同 —— 重建后行为会变，须由 ROUND-B 复验。

#### (d) 最终判定（AG4-12 已撤回）

| 层 | 事实 | 判定 |
|---|---|---|
| 行为 | DrawerPreview 渲染成功、**presign 0 次**、改走 `previewStream` 200、`canvas=1` | **已验** |
| 包内实现 | `nh` 对 office/sheet 在 presign 之前 return | **行为与包一致 → 设计分流，非缺陷** |
| HEAD 源码 | 已改为"所有类型先 presign"，但**不在本包**（13:34:50 > 13:22:11） | **已知版本漂移**；重建后由 **ROUND-B** 复验 |
| 失败三态文案 | 本包内该路径不发 presign → 文案**未触发**（三态代码在包内存在） | **UNVERIFIED（未触发，非未实现）** |

**结论（TL 定稿口径）**：
> 预览抽屉对 **Office 类型**不调 presign、直接走 `previewStream` —— 与包内实现一致，属**设计分流，不是缺陷**；
> **该分流按传入的 `fileType` 判定：office/sheet 之外的其它类型（含 `table`）会走 `nh` 的 else 分支并调 presign**，
> 因此**不能从"预览抽屉不调 presign"推出"所有类型都不调"**（见下方交叉证据）；
> 该包不含 13:34 的 FIX-04（改成"所有类型先 presign"），**重建后需 ROUND-B 复验**。

**三个抽屉各自的证据等级（一张观察不能摊到两个组件上）**

聊天页有两个抽屉（`drawerType="mark"` → DrawerContent；`"preview"` → DrawerPreview），加上详情页的 `StreamReader` 抽屉，一共三格。本报告的覆盖情况：

| 抽屉 | 组件 | 本轮证据 | 判定 |
|---|---|---|---|
| 知识库详情页文件抽屉 | `StreamReader` | **AG-2 实测 0 命中**（`page.on('response')` 按 URL 匹配） | 已验（不调 presign） |
| 聊天**内容**抽屉 | `DrawerContent` | **本轮无人实测**（我这一点开的是 preview 抽屉，`#pdfBox` 已证）→ 其"不调 presign"仅为**二级推定** | **UNVERIFIED** |
| 聊天**预览**抽屉 | `DrawerPreview` | **AG-4 实测 0 命中**（`.docx`/office 场景）+ 包内 `nh` office 分支解释 | 已验（office 场景不调，非缺陷） |

> 这一格专门防"一条路径推成两个入口"：内容抽屉（mark）与预览抽屉（preview）是**两个不同组件**，任何一格的观测都不能替另一格作证。

**两条入口"结果相同、成因不同"（避免被读成"行为一致"）**

| 入口 | 不调 presign 的**机制** |
|---|---|
| 知识库详情页文件抽屉（`StreamReader`） | 走 `/preview/convert?key=…` 时**被包装器的短路分支接住** → 直接 `previewStream` |
| 聊天预览抽屉（`DrawerPreview` → 包内 `nh`） | **office/sheet 分支在 presign 之前 `return`** → 直接 `previewStream` |

两者在 office/sheet 场景下**结果相同（都不发 presign）**，但**是两条独立成因**；写成"行为一致"会掩盖这一点，后续修复可能只改一处而漏另一处。

**else 分支（pdf / table / 图片）**：**UNVERIFIED（已批准未执行）**，且**不单列观测、不挂任何人**。
协调侧裁定原文口径：重建后 `nh` 即"全类型先 presign"版本，**pdf 分支这个问法本身会消失**，
届时所有类型均走 presign，该分支问题不再存在 → 由 **ROUND-B 的 S5-08 天然覆盖**。
（因此本报告不写"待某人补"——**没有这个待办**，单独测等于测一个即将消失的分支。）

> **方法论（三条纪律合并，本报告采纳）**：
> ① 判定**运行行为**时，代码只能来自**包内（bundle 抠出）**或**行为观测**；源码 + git 时间只能解释"为什么包内是那个样子"，**不能断言"包内应该怎样"**。
> ② 判"某条路径调不调"只能由**一级证据**下，且一级证据必须同时带 **路径域 + 类型域** —— 同一个抽屉，`docx` 与 `table` 的结论相反（见上方交叉证据表）。
> ③ **一级证据定结论，二级证据只解释机制**；二级不能单独定"谁发起、走哪条分支"（例："presign 由组件自己调"仅二级推理、无一级证据 → 只能标 UNVERIFIED）。
> 本次两次误判（用 HEAD 源码当包内应然；把 docx 结论外推到整条路径）分别踩中 ①②，撤回记录保留以便追溯。

证据：`RA-final.json`、`RA-identify.json`、`RA-result.json`、`RA-20-preview-drawer.png`、`RA-e3-panel-item.png`、`S8-ref3-result.json`；包内实现=**AG-2 提供（`nh`）**。

### 2.7 独立后果 R1：流式输出在失败前已提交不可撤回的内容（错误答案先于错误提示到达用户）

**这一条是独立后果，不是 AG4-11 的附属描述**：即使 global 的实现被修好，只要"失败路径"还在，它就会复发。

逐帧事实（`/qa/ai/question_re`，globalMode=true，3/3 一致）：

```
帧 1..14（status=1，正常流式）：逐字吐出 →「智造贷的最高额度为人民币5000万元。」
帧 15   （status=3，错误终态）：追加   →「模型暂无法返回，请稍后再试!!!」
```

用户侧实际观感（UI 截图同款）：先读到一句语法完整、带具体数字、看起来就是答案的话（5000万元），
**错误提示最后才到**。此时：
1. 前半句已经渲染进对话历史，**不可撤回**（UI 不撤回已渲染内容，实测 3/3 都保留）；
2. 用户很可能已把 5000 万当成结论（真实口径 8000 万，差 3000 万）；
3. 复制/转发/截图发生在错误提示出现之前的窗口内，事后无法追溯纠正。

**为什么它与"答案错"不是同一件事**：
- "答案错"（AG4-01）是内容问题——把错的数字修对即可；
- "失败前已提交内容"（本条）是**协议/时序问题**——只要失败发生在流式过程中，就会把半成品当成答案交付。
  两者的修复点不同：前者改事实选择/摘要代次，后者要改"失败时是否撤回/标记已输出内容"的机制。

**可复现的最小判据**（供回归时直接用）：
`frames[-1].status == 3` 且 `累加(answer 帧) != ""` → 即"失败但已输出内容"，判 FAIL。
本次实测 3/3 命中（`E-re-frames-summary.json` 的 `has_5000=true` + `final_status=3`）。

> 该判据的价值：**它不依赖 global 修没修好**——任何"流式输出中途失败"的路径都适用，可作为通用回归断言。

**修复方向不要落成文案问题（TL 提醒，本报告采纳）**：
这后半句（"失败时是否撤回/标记已输出内容"）**不只是前端或产品口径问题**——
流式协议本身需要"**可撤销帧**"或"**终态标记先于内容**"的设计，
否则**任何后端失败都会以同样方式泄漏**（今天泄漏的是 5000万，换个功能泄漏的可能就是别的数字）。
把它当文案修（例如把错误提示措辞改得更醒目）只能缓解观感，不能消除"错答案先到、错误后到"的时序缺陷。

**定级归属（TL 最终拍定）**：本条并入 **AG4-11 = P0**。定级理由不在"错误是否频繁"，而在**面向用户的 global 整条不可用 + 该端点根本没实现 global + 失败前已泄漏旧值**三者叠加（§2.8）；一旦叠加"开关视觉上是开的、用户以为自己在用 global"，用户既不知道功能没接上，也来不及区分哪半句是错的。
**仍需保留的死条文（TL 指定，原文照录）**：**若产品侧吞掉错误提示或静默重试，AG4-11 的泄漏后果升级独立计数** —— 因为那会把"看得见的失败"变成"看不见的错值"，届时应单列一条，不再挂在 AG4-11 名下。

### 2.8 两个端点的分工：代码里有明确分工，且 global 只在其中一个实现（TL 问的那句话）

**结论：有明确分工，不是猜测；而且这条分工正好解释了 UI 为什么 status=3。**

| 端点 | `AiController` 上的接口文档原文（`interfaces/AiController.java:48-81`） |
|---|---|
| `POST /ai/question` | 「检索召回接口和模型推理接口，**返回接口拼接在一起**」→ `aiService.question()` |
| `POST /ai/question_re` | 「检索召回接口和模型推理接口，**返回结果未拼接**」→ `aiService.questionRe()` |

即 `_re` = **返回结果未拼接**版本（不是"带引用版"，也不是"流式重写版"）。

**实现层的关键不对称（这才是 status=3 的机理）**：
- `publicQuestion()`（`/question` 走的）：含 global map-reduce 直答分支 ——
  `boolean reqGlobalMode = ...getGlobalMode()`、`reduceAnswer = alParams.getString(GLOBAL_ANSWER)`、
  且 `R14-C-FIX-10` 明确「global 模式且 reduce 没给答案时**不要回落到模型生成**」（`AiServiceImpl.java:653-665, 822-836`）。
- `publicQuestionRe()`（`/question_re` 走的，`AiServiceImpl.java:276-541`）：**通篇没有 `global` / `GLOBAL_ANSWER` 任何处理**，
  直接 `return modelBasedInferenceRe(docs, ...)` 走普通生成 → 模型拿到的是"社区摘要"当参考资料，
  生成失败即 `status=3`，而在此之前已经把摘要里的旧值流了出去。

→ 一句话：**global 能力只在 `/question` 实现；UI 实际调用的 `/question_re` 没有这个实现**。所以 UI 用户的 global 不是"偶发失败"，是"这条路径根本没接上 global"。

**该端点是否属于对外能力（回答 TL 的 (a)/(b) 择一）**
- `contracts/` 与 `specs/` 中 **零登记**（`grep -rln "qa/ai/question" contracts/ specs/` 无命中）→ 不是合同级/对外 SDK 能力；
- 但 `docs/r12/r14/B-GLOBAL-GOLD.md:6` 称其为「**用户入口** `/qa/ai/question`」，前端 `AIChat/services/apis.tsx:32` 也把 `chat_start` 声明为 `/qa/ai/question`（而真实流量走 `question_re`，与声明不一致）；
- 故按 TL 口径 **(b)**：用户主路径不直接打它（真实流量在 `question_re`），影响面限于"照文档/前端常量直接集成该端点的人"。
- **定级最终按 TL 拍定（以此为准；此前"有无错误终态"那条线已被 TL 本人改口覆盖，勿再引用）**：
  - **AG4-01 = P0**：错误数值当作"成功答案"交付（status=2、单帧、无错误终态）；
  - **AG4-11 = P0**：UI 假开关（`question_re` 未实现 global）+ 失败前泄漏旧值（§2.7 R1 / §2.9）。
- 定级口径：**保守优先** —— 两条各自满足一个 P0 判据、修法不重叠；宁可多阻断一条，也不因"用户主路径不经过"而降级（降级＝排到下一轮，而问题不会自己消失）。两者**独立机制、分开记录、不合并**（理由见 §3 块）。

### 2.9 为什么 AG4-11 是 P0：这个开关是"假开关"（TL 指定必须写进报告）

**"假开关"的定义**：它能点、视觉会变、请求体也老老实实带上了 `globalMode:true`，**但服务端那条路径根本不读这个字段**。

实测三个层次，全部为真：

| 层 | 事实 | 证据 |
|---|---|---|
| 交互层 | 点击后按钮变蓝、`localStorage r13_global_mode` 1↔0、「GraphRAG 全局」角标出现 | `S8-01/03-*.png` |
| 传输层 | 请求体确实带 `"globalMode":true`（关时无此字段） | `D-ui-request-body.json`、`S8-result.json` |
| **服务端** | UI 实际命中的 `/ai/question_re` → `publicQuestionRe()` **通篇无 global 处理**；global 只在 `/ai/question` 实现 | `AiServiceImpl.java:276-541` vs `653-836` |

**为什么这比"功能报错"更糟**（TL 原话，本报告采纳）：
报错时用户知道不能用，会换路径或找人工；**假开关让用户以为自己在用**——他会把界面上那句"GraphRAG 全局"当作能力已生效，
进而相信（本不该相信的）摘要级结论，且在失败提示出现前就已经读完半句错答案。

这也是把 AG4-11 定为 **P0** 而不是"偶发失败 P1"的核心理由：**失败是可见的，但"开关无效"是隐形且先于失败发生的。**

---

## 3. 缺陷清单（11 条：P0 2 / P1 2 / P2 3 / P3 4）

**编号说明**：TL 建议把「摘要未收敛 + 读写两侧不一致」做成独立条目并命名为 AG4-11；该编号在上一轮已被 `question_re` 生成失败占用（TL 已确认的拆分），故**根因条目沿用 AG4-03**，`question_re` 失败条目保持 AG4-11。两者内容不重叠：AG4-03 = 数据代次 / 读端写端；AG4-11 = 生成链路错误终态。

**两条都是 P0，但必须分开计数（TL 最终定稿，本报告采纳）**

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

| 编号 | 级别 | 缺陷 | 证据 |
|---|---|---|---|
| AG4-11 | **P0** | **面向用户的 global 是"假开关"：UI 实际走的 `/qa/ai/question_re` 未实现 global，3/3 以 status=3 收尾，且失败前已泄漏旧值**。3/3 终态 `status=3`、refs=0；同端点关模式 3/3 正常（status=2 / 8000万 / refs=1）。代码级机理（§2.8）：`publicQuestionRe()` **没有 global 分支**（`GLOBAL_ANSWER` 只在 `publicQuestion` 里处理），global 只在 `/question` 实现。**子后果**：前 14 帧已提交「5000万元」，错误提示晚于错误答案到达（独立后果 R1，§2.7）。**复核条款**：若改为吞掉错误提示或静默重试，泄漏将完全不可察觉 → 维持/升为 P0 | `E-re-frames-summary.json`、`E-re-on-{1,2,3}.sse.txt`、`D-ui-request-body.json`、`AiController.java:48-81`、`AiServiceImpl.java:276-541,653-836` |
| AG4-01 | **P0**（TL 最终定级：错误数值被当作"成功答案"交付；判据=用户无法察觉地拿到错答案） | **额度题"答案 / 引用 / 原文"三者两两不符（三个数字互不相符）**，详见 §3.1 专表。真相=8000万元（V1，local 3/3）；global 走 `question` 得 **1000万元**（status=2、单帧、无错误终态）、走 `question_re`（UI 实际链路）得 **5000万元**；被引社区 `L0-18625408` 正文写「最高额度 5000万元」，同一社区正文另含「人民币1000万元 -信用方式上限-> 智造贷」。即模型把**信用方式上限 1000万**当成**最高额度** | `D-tl-three.json`、`D-endpoint-compare.json`、`B2-amount-onoff-3x.json`、`S8-on-run1~3.png` |
| AG4-02 | P1 | **global 引用与结论不匹配（回链语义段断裂）**。G1 三条结论统一标注 `[L0-18625408]`，该社区正文只讲智造贷额度/期限/流程，不含任何企业评级与加点；60 个基点在被引原文与被引社区正文中均不可得 | `C-community-index-raw.json`、`B1-global-G1-3runs.json`、`B6-number-support.json` |
| AG4-10 | P2 | **§1.7 假拒答（与 AG4-01 独立条目）**。「智造贷的授信额度是多少？」global 开 **3/3** 返回「事实中未提及 [L0-18625408]」，而该事实在库（ES 有 V0/V1 两块额度事实）且所引社区正文亦写「最高额度 5000万元」。**排除 ENV_EVENT 的推理链**：①同批 G1 加点题 3/3 正常作答（30/60/60，带社区标记）；②`community_summary_kb_9` 7 条社区全部在线，直调 `query_community` 返回 `code=200`；③非"同批全类别无来源拒答"形态（所引社区 source 非空） | `A3-global-3runs.json`、`C-community-index-raw.json` |
| AG4-03 | **P1**（级别由 TL 最终定） | **社区摘要索引未随版本/删除收敛，且写入端与读取端不是同一份数据（根因条目）**。①**读取端 ES**：`community_summary_kb_9` 7 条，`create_time` 全在 `2026-10-27 11:06:35~49`（TL 侧读到 11:06:49，一致），`update_time` 同一刻批量写，`has8000=False`；`metadata.file_ids` = `['119','120','226','234','258','259','260','266','268']` / `['263','271']`，**这些 id 在当前 ES 中已不存在**（现存 290/328/330/331/332/333/334/343/329）；核心社区 `L0-18625408` 正文写「智造贷 -最高额度-> 人民币5000万元」。②**写入端 Milvus**（协调侧独立核对）：`graph_base._community_summary_kb_9` `row_count=1`，唯一一条 `create_time=2026-10-27 14:56:31`。③问答读 ES（`_load_summaries` 读 `community_summary_kb_9`）。**解释力**：一条根因同时解释 ①global 额度题给 5000万（AG4-01）、②global 引用与结论不匹配（AG4-02）、③引用带文件级悬空（此前 GRAPH_PROVENANCE 已报"文件级悬空"）。**边界**：只能解释"为什么是 5000万"，解释不了"为什么 `question` 是 1000万"（那是事实选择错，属 AG4-01）。**待确认（保留，不由本角色下结论）**：图侧曾报 `generate_community` 24s、社区7/摘要7/失败0，但 ES 侧 11:06 之后无任何写入 —— 属"声称成功但未落库"的**候选**，需图侧确认当时写入的是哪个存储/哪个 kb | `D-tl-three.json`（时间线并列）、`C-community-index-raw.json`、`A2-es-version-facts.json`；Milvus 侧=**协调侧独立核对** |
| AG4-04 | P2 | **图谱页对 admin 全拒**。`/graph/info/nodes`、`/graph/info/edges`、`/graph/graphStatistics/getWholeGraphStatistics` 均 `401 / 30021 没有足够的权限`（换 spaceName 为 kb_9 / 中文名 / g_kb_9 结果一致），页面仅显示 `节点数 0/0 关系数 0/0`，无任何提示；而底层图数据存在 | `S11-network.json`、`S11-02-visual-allgraph.png`、`C-graph-query-graphdata.json` |
| AG4-05 | P2 | **版本管理无 V0/V1 标识与切换**（历史缺口未修）。整页 `V[0-9]` 命中 0 次；「版本号」列被注释；展开分组后只有文件名；无任何版本选择控件，V0 内容问答不可达 | `S10-04-version-group-expanded.png`、`S10-expand-result.json`、`S10-result.json` |
| AG4-06 | P3 | **图谱解析失败的文件在图谱增强列表不可见**：`docx-plain.docx` 的 `graph_parse_status=4`（失败），但 `fileListType=3` 列表 `total=0`，用户既看不到失败态也无法点「重新解析」 | `S11-result.json`、DB 只读核对（见正文 2.3） |
| AG4-07 | P3 | **社区摘要引用缺来源**：`L0-be7452ca`、`L0-3c882b30` 的 `sources=[]` 且 `sources_resolved_by=""`；后者正是拒答引用的对象，表现为 `refs=1` 但 `metadata.source=""` | `C-community-index-raw.json`、`A3-global-refusal.json` |
| AG4-08 | P3 | **检索层白名单丢弃溯源字段**：经 19995 `retrieval_documents` 返回的块 `provenance_quality / recovered_by / identity_stability` 均为 `null`（19529 直连时为 `exact_chunk`）。不能据此判"溯源失败"，本角色已改用 `chunk_pk ∩ ES._id` 的存储事实判定 | `B8-graph-only-on.json` vs `C-graph-query-graphdata.json` |
| AG4-09 | P3 | **global 输出形态在两条链路上差异极大，用户无法复核**：①额度题 `question` global 开只有 1 帧、~2.0s，答案是社区事实模板直拼（`statuses=[2], frames=1`），同题 local 为 39 帧/~17s；②G1 同题：UI 首轮 global 开答「无法直接获取…」（拒答），API 同 body 3/3 正常作答 30/60/60；③UI 侧出现错误文案但 HTTP 仍是 200（错误只体现在 SSE 的 `status=3` 帧，HTTP 层不可见） | `C-sse-summary.json`、`C-on-1.sse.txt`、`E-re-frames-summary.json`、`S8-result.json`（`global_on` 步骤） |

### 3.1 AG4-01 专表：三个数字互不相符（TL 指定写法）

| 口径 | 数值 | 出处（可复核） |
|---|---|---|
| **真相**（有效版本 V1，local 3/3 一致） | **8000万元** | `D-tl-three.json` → `local_off[1..3]`「智造贷单户最高授信额度为人民币8000万元。」；ES V1 块（fid=328）正文「单户最高授信额度为人民币8000万元」 |
| **global —— `/qa/ai/question`（API 直连）** | **1000万元** | `D-endpoint-compare.json`：「智造贷最高额度是1000万元 [L0-18625408]。」（3/3 一致，单帧、status=2） |
| **global —— `/qa/ai/question_re`（UI 实际走的）** | **5000万元 + 错误态** | `E-re-frames-summary.json`：失败前累计「智造贷的最高额度为人民币5000万元。」→ 末帧「模型暂无法返回，请稍后再试!!!」（3/3，终态 status=3） |
| **被引社区 L0-18625408 正文** | **5000万元** | `C-community-index-raw.json`：「智造贷 -最高额度-> 人民币5000万元」 |
| **同一社区正文的另一条事实** | **1000万元** | 同上：「人民币1000万元 -信用方式上限-> 智造贷」 |

**因果拆分（两条不同因，不可合并）**

| 现象 | 成因 | 对应条目 |
|---|---|---|
| 为什么是 **5000万** | 社区摘要停在上一次代次（11:06），只含 V0 口径，不含 V1 的 8000万 | **AG4-03** |
| 为什么是 **1000万** | 同一社区里的「信用方式上限 1000万元」被当成了「最高额度」——**事实选择错误**（把子限额当总额度） | **AG4-01** |
| 为什么 UI 还多一句报错 | `question_re` 生成阶段失败，终态 `status=3`，但失败前已流出旧值 | **AG4-11** |

→ 因此 **AG4-03 不能解释 AG4-01**：即使社区摘要更新到 V1（问题消失后 5000万 不再出现），`question` 仍可能把 1000万 当最高额度返回；反之把事实选择修好，摘要不重建时仍会返回 5000万。两条都要修。

---

## 4. 判据修正（原任务书判据不成立，已替换）

**4.1 原判据**：任务书 S8 要求「开时答案跨文档、关时不跨」。

**4.2 为何不成立**——用引用条数一测就出反结论：

| 模式 | refs 条数 | 引用来源 |
|---|---|---|
| global 开（同题 G1） | **1** | 仅 `…/R12FIX-product-intro.pptx/V1/…` |
| global 关（同题 G1） | **3** | `credit-ledger.xlsx/V0`、`intro.pptx/V1`、`loan.docx/V1` |

若按"跨文档=引用≥2 个文件"判，会得出"**关才是跨文档、开反而不跨**"的反结论，与设计意图完全相反。根因：global 的引用粒度是**社区→文件级**（一个社区只解析出一条 source），local 的引用粒度是**块级**（一条结论一个块）。**粒度不同的两个量不能直接比大小。**

**4.3 新判据（已用于本报告全部判定）**

判"是否为全局模式"看 **答案的产出形态**，不看引用条数：

1. 答案正文出现社区标记 `[L0-xxxxxxx]`（或 `[L1-…]`）；
2. 引用对象的 `metadata.search_type` 含 `graph_community`、`metadata.community_id` 非空、`title` 形如「社区摘要 L0-…」；
3. 引用条数天然为 1~2（社区粒度），**不参与判定**。

**4.4 如何证伪这条新判据（不能只证成立）**

| 证伪尝试 | 结果 |
|---|---|
| 关模式是否也会出 `[L0-*]`？ | 否：关模式答案无任何 `[L0-*]`，`search_type` 无 `graph_community`（`B2`、`D-endpoint-compare`） |
| 开模式是否可能不走社区（直接块级）？ | 会：`question_re` 关模式 `search_type` 也无 graph_community；说明该标记只由 global 开触发，不是"总会出现" |
| 标记是否可能来自模型幻觉？ | 否：标记与引用对象 `community_id` 一一对应，且直调 `query_community` 返回同 id 社区（`C-community-index-raw.json`） |
| 引用条数能否单独作为判据？ | 否，见 4.2 的反结论 |

→ 新判据可被上述任一情形推翻；实测四条都站得住，故采用。**这也是本报告唯一一处与任务书原文口径不一致的地方，已在 §1 总表 S8 对应行标注"判据=社区标记，非跨文档"。**

---

## 5. NOT RUN / UNVERIFIED（附原因）

| 项 | 状态 | 原因 |
|---|---|---|
| S10「分别问 V0 / V1 并核对 V0 引用指 V0」 | **BLOCKED** | 界面无 V0 选择入口（AG4-05），无法构造"问 V0"的用户路径 |
| S11「实体追溯 / local 多跳（页面路径）」 | **FAIL（页面不可达）** | 图接口 401，页面上没有可点的实体节点（AG4-04）；多跳改由检索层 19995 开/关对照取证 |
| S8「点击引用展开原文」→ **渲染是否可用** | **PASS（已升级，不再 UNVERIFIED）** | 已实测：点「知识溯源」→ 点条目 → `previewStream` 200 + 抽屉打开 + `canvas=1` 实渲染。见 §2.6 |
| S8「点击引用展开原文」→ **presign 前置校验：office/sheet 分支** | **已验（无缺陷，缺口关闭）** | ROUND-A 完成：抽屉=**DrawerPreview**（`#pdfBox`/事件链/占位三条证据）；`.docx` 源 hits=0，与包内 `nh` 的 office 分支一致 → **设计分流，非缺陷**。原记 AG4-12 已撤回 |
| S8「点击引用展开原文」→ **presign 前置校验：else 分支（含 pdf / table）** | **UNVERIFIED（已批准未执行）** | 按包内 `nh`，office/sheet 之外的类型走 else 分支**会调 presign**；本轮未走该分支、未由本角色观测。协调侧裁定：**不再单做 pdf 观测**——重建后 `nh` 变为"全类型先 presign"，该问法消失，由 **ROUND-B 的 S5-08 天然覆盖** |
| S8「点击引用展开原文」→ **失败文案三态（404·403·5xx）** | **UNVERIFIED（有证据，非功能缺失）** | 该路径不发 presign → 三态文案**未触发**；三态代码在 entry chunk（`de242450…`）内存在，属"未触发"而非"未实现"。global 的社区级引用亦无"定位到具体块"路由（`chunk_refs` 粒度为社区级），点击只能打开文件级原文 |
| 截图级复核 | 已完成 | 见第 5 节索引（23 张 png + 6 份 SSE 原文 + 31 份 JSON + 9 份 DOM 快照） |

---

## 6. 证据索引（`AG-4/evidence/`）

- 版本自证：`S0-version-selfproof.md`
- 只读 API 探针输出：`A0-kb-list.json`、`A1-version-groups.json`、`A2-es-version-facts.json`、`A3-global-onoff.json`、`A3-global-3runs.json`、`A3-global-refusal.json`、`A4-version-default-answer.json`、`A5-graph-facts.json`、`A5-graph-pk-vs-es.json`
- 第二轮：`B1-global-G1-3runs.json`、`B2-amount-onoff-3x.json`、`B3-ask-version-explicit.json`、`B4-refusal.json`、`B5-citation-chain.json`、`B6-number-support.json`、`B7-graph-onoff-retrieval.json`、`B8-graph-only-on.json`、`B9-graph-provenance.json`
- 存储事实：`C-community-index-raw.json`、`C-graph-query-graphdata.json`、`C-on-{1,2,3}.sse.txt`、`C-off-{1,2,3}.sse.txt`、`C-sse-summary.json`
- TL 追加三项：`D-tl-three.json`（①global 5000万原文 ②local 8000万对照 ③摘要 vs ES chunk create_time 并列）
- 端点归属：`D-endpoint-compare.json`（`question` vs `question_re` × 开/关 四格）、`D-ui-request-body.json`（CDP 抓 UI 真实请求体 + 逐帧）、`E-re-frames-summary.json`、`E-re-on-{1,2,3}.sse.txt`、`E-re-off-1.sse.txt`
- 引用路径实测（§2.6）：`S8-ref3-result.json`、`S8-ref3-network.json`、`S8-ref3-01-panel.png`、`S8-ref3-02-after-click.png`、`S8-ref2-result.json`、`S8-ref2-01-source-expanded.png`、`S8-ref2-02-after-click.png`、`S8-ref-01-answer.png`
- S8 截图/网络：`S8-00-before.png`、`S8-01-global-on-flag.png`、`S8-02-global-on-answer.png`、`S8-03-global-off-flag.png`、`S8-04-global-off-answer.png`、`S8-on-run1~3.png`、`S8-off-run1.png`、`S8-network.json`、`S8b-network.json`、`S8b-result.json`、`S8-result.json`
- S10：`S10-01-version-tab.png`、`S10-02-version-expanded.png`、`S10-03-file-tab.png`、`S10-04-version-group-expanded.png`、`S10-result.json`、`S10-expand-result.json`、`S10-network.json`
- S11：`S11-01-graph-tab.png`、`S11-02-visual-allgraph.png`、`S11-03-entity-click.png`、`S11-result.json`、`S11-network.json`
- 脚本：`get_token.py`、`lib.js`、`probe_api.py`、`probe_api2.py`、`probe_api3.py`、`probe_sse_raw.py`、`s8_global.js`、`s8_ui_repeat.js`、`s10_version.js`、`s10_expand.js`、`s11_graph.js`、`explore_*.js`

复现命令（只读）：

```bash
cd /home/szf/data/dev/llmke-r12/platform/r12/qa/e2e-run-20261027T2357/AG-4
/home/szf/data/dev/llmke-r12/platform/r12/venvs/alg/bin/python get_token.py
/home/szf/data/dev/llmke-r12/platform/r12/venvs/alg/bin/python probe_api.py     # A0~A5
/home/szf/data/dev/llmke-r12/platform/r12/venvs/alg/bin/python probe_api2.py    # B1~B7
/home/szf/data/dev/llmke-r12/platform/r12/venvs/alg/bin/python probe_api3.py    # B8
/home/szf/data/dev/llmke-r12/platform/r12/venvs/alg/bin/python probe_tl_three.py  # D
/home/szf/data/dev/llmke-r12/platform/r12/venvs/alg/bin/python probe_re_frames.py # E（question_re 逐帧）
NODE_PATH=/home/szf/env/my-playwright/node_modules node s8_global.js
NODE_PATH=/home/szf/env/my-playwright/node_modules node s8_ui_repeat.js
NODE_PATH=/home/szf/env/my-playwright/node_modules node s8_ui_body.js   # CDP 抓 UI 请求体+逐帧
NODE_PATH=/home/szf/env/my-playwright/node_modules node s10_version.js
NODE_PATH=/home/szf/env/my-playwright/node_modules node s10_expand.js
NODE_PATH=/home/szf/env/my-playwright/node_modules node s11_graph.js
```

> 注：`s8_sse_capture.js` 为一次未成功的尝试（Playwright 对 SSE 流在 `response.text()` 上会挂住），已弃用；SSE 原文改用 `probe_sse_raw.py` 落盘，结果在 `C-on-*.sse.txt` / `C-off-*.sse.txt`。
