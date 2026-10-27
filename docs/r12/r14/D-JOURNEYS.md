# D｜前端与用户旅程（R14 / Loop 4）

> 写作口径：只写**从页面点出来**的结果。"接口通"不等于"页面可用"，两者分列。
> 证据目录：`platform/r12/qa/evidence/R14-UI-20261027T022341Z/`（截图 + 每次运行的 run log）
> 浏览器：Chromium（Playwright 1.60）真实渲染，1600×1000，非 JSDOM、非接口脚本。
> 采集时间：2026-10-27 10:20–10:50（其间栈多次抖动，逐条标注了时刻）

---

## 0. 会话建立方式（必须先读，否则证据定级会错）

- `/auth/user/login` **强制 4 位图形验证码**。验证码明文确在 `r12-redis`（`captcha:md5(ip+ua)`），但值经 Redisson 序列化为二进制（实测 hex `03 78 77 37 ed`），冷环境无法可靠还原；把验证码图放大 5 倍后 kaptcha 干扰线仍使人读不可靠。
- 因此**会话由 `POST /auth/user/simpleLogin` 建立**（服务端既有端点，与页面同一 AES-128-CBC/ZeroPadding 密码链），随后按前端 `AppPassport` 完全相同的结构写入 `localStorage["gitech_ril:rag_ai"].userInfo.token` + cookie `rag_ai_token`，再跳转 `/`。
- **本报告中的 12 条旅程一律是真实页面点击**，但**不得**把"登录"本身记作通过项。TL 已确认接受该方式，并要求写明。原文：`会话由 simpleLogin 建立（验证码自动化受限），页面操作真实`。
- 附带的独立发现（安全，非本轮修复项）：`UserController.java:59` 的 `/user/simpleLogin` 标注"用户登录（不需要验证码）"，**无任何开关门控、无 `@OperationLog` 审计**，直接走同一 `userInfoDomainService.login`。即能访问 8088 的任何人可跳过验证码无限次试密码 → 图形验证码作为暴力破解防护实际无效。建议单列 C16 隐患条（D 未改，属 C/B 域）。

---

## 0A. 最终状态一页版（2026-10-27 12:50，供 TL 合并进总报告）

> 口径：**"页面可用"= 页面里真看见内容**；接口 200 不算通过。每条用独立浏览器上下文，避免残留 viewer 造成假绿。
> 环境窗口：E 已声明 10:42–12:17 为基础设施故障期，该窗口内所有结果作废；下表只采信 12:27 之后的复测。

| # | 旅程 | 最终状态 | 一句依据 | 证据 |
|---|---|---|---|---|
| 1 | 管理员建用户/部门/组→授共享→撤权 | **NOT RUN**（页面入口已验证可用） | 部门/分组/角色三页可打开、新建弹窗可用；写操作需与 F 的权限域用例排期，避免互相覆盖 | `J4-*` `J6-03-create-kb-dialog.png` |
| 2 | 普通用户建库/目录/标签策略/批量上传 | **NOT RUN** | 写入类；kb_9 期间被他人反复重解析，写入会被覆盖 | — |
| 3 | 成功/失败/重试/排队状态 + 打开原文 | **PASS** | 状态与重试入口可见；**详情页四类原文全部能看见内容**（pdf canvas 1/1、docx canvas 1/1、pptx canvas 1/2、xlsx 表格文本完整） | `final/PF-*` `final/KP2-*` `J3-01-file-manage.png` |
| 4 | 语义改写/多轮/取消/重登录历史 | **多轮 PASS｜历史 PASS｜取消 FAIL(库不支持)｜语义改写 NOT RUN** | 后端 `chat_history` 确实携带上一轮；`reload` 后会话仍在；流式中**无停止/取消控件**（全量扫 button/aria/title 无 stop/cancel） | `J2b-04` `J2b-05` `J2b-06` |
| 5 | FAQ 抽取→编辑/启停/直答/删除 | **启停 PASS｜失败可见性 PASS｜抽取/编辑/删除 NOT RUN** | 健康时 200 且状态真实翻转；货真价实的 500（jar 缺类）时页面显示「问答对启用失败：…」且开关不回落 | `final/RT-03` `after-build2/RT-03` |
| 6 | V0/V1 差异问答 + 原版本引用 | **FAIL（入口不可达）** | 版本管理页只显示文件分组，全文无 `V0`/`V1` 标识与对比入口 | `J3-02-version.png` |
| 7 | 表格筛选/聚合/数值单位/结构化查询/恶意拒绝 | **部分：表格可看 PASS；筛选未见入口；恶意 SQL NOT RUN** | 直连库 `r13-sql-guard-test` 表数据可查看（含表头/行数）；页面未发现筛选/搜索控件 | `J7-01` `J8-01` |
| 8 | 图谱可视化/实体追溯/合并回滚/local 多跳 | **FAIL（无数据）** | kb_9「图谱增强」= 暂无数据（0 行） | `J3-03-graph.png` |
| 9 | global 跨文档回答 + 原文回链 | **PASS** | 开关**双向**：开→`localStorage=1`+顶部标识+请求体带 `globalMode`；关→`0`+无标识+不带 | `final/RT-04` `final/RT-05` `global-bypass.log` |
| 10 | 同名/更新/删除/重解析后检索收敛 | **NOT RUN（他人并发）** | 观察到 `5000万` 与 `8000万` 两条并存于 ES（`R12FIX-product-loan.docx` 与 `...(1).docx`），属该旅程问题域 | ES 查询记录见 §2 行 10 |
| 11 | 无权/撤权/缓存旧 session/直接访问/伪头/无效配置 | **部分 PASS**：未登录→挡回登录；伪 token→`getMenusByUser` 401→回登录；其余 NOT RUN | 页面级两条负例成立 | `J6-01-noauth.png` `J6-02-forged-token.png` |
| 12 | 故障恢复/备份还原/升级回退后同旅程 | **NOT RUN** | 属 E/C 的恢复演练时间点；今日 10:42/11:01/11:47 三次故障是"故障"不是"已验证恢复" | `J6.log` |

**贯穿性技术债 / 能力缺口（非"未测"）**：F-D-15 全局开关依赖 inline style 颜色判定（已批准临时方案，`TODO(R14-D-FIX-03)` 已写入代码）；F-D-16 流式取消 = `@gientech/modual` 不支持 abort，**非前端可解**（C09 记 FAIL）。

**问答抽屉（13:26–13:32，entry `index-CpE2zvYY.js`）—— 已闭环**

| 类型 | 实际接口 | 状态 | Content-Type | 页面层 | 证据 |
|---|---|---|---|---|---|
| pptx（Office） | `previewStream` | 200 | `application/pdf` | PASS，canvas=1，页码 **1/2** 94% | `final/CF-R12FIX-product-intro.pptx.png` |
| docx（Office） | `previewStream` | 200 | `application/pdf` | PASS，canvas=1，页码 **1/1** 111% | `final/CF-R12FIX-product-loan.docx.png` |

> 两个文件分两次运行验证：抽屉打开后会遮住引用列表，无法在同一次会话里连续点第二个（这不是产品缺陷，是验收脚本的交互限制）。

**结论**：R13 遗留的「问答点引用打不开原文」**在详情页与问答抽屉两侧都已闭环**（详情页 4/4、抽屉 Office 2/2，均为"页面里真看见内容"）。

**「如何证明测的是哪一版」**（响应 TL 要求写进报告）
```bash
# 1) 入口 chunk 必须"宿主 == 容器"（防 bind mount 钉旧 inode）
grep -o 'index-[A-Za-z0-9_-]*\.js' frontend/plateform/dist/index.html | head -1
curl -s http://127.0.0.1:18088/index.html | grep -o 'index-[A-Za-z0-9_-]*\.js' | head -1

# 2) 用特征串证明目标改动在包里（比 mtime 可靠）
grep -l "无权访问该原文"   frontend/plateform/dist/assets/*.js   # 错误分类已进包
grep -l "原文不存在或已删除" frontend/plateform/dist/assets/*.js
grep -l "原文服务异常"      frontend/plateform/dist/assets/*.js
```
本次实测：入口 `index-CpE2zvYY.js`（宿主/容器一致），三条特征串各命中 2 个 chunk。

> **通用要求（建议写进 R14 交付纪律）**：任何交付物的"已生效"判断，必须来自**它自身产物的内容**（哈希 / 标识 / 数字），不能来自**过程信号**（HTTP 200、日志有行、命令返回 0）。
> 今日两次实证：① 宿主换目录后 bind mount 仍钉旧 inode，`curl 资产` 返回 200 但内容是 **SPA fallback 的 index.html**（size/md5 对不上）；② 只看"页面能打开"会验到一个根本没更新的旧包。

**仍未端到端验证的一条**：503/403/404 三类**失败文案**的 UI 展示。当前实现里 presign 前置校验覆盖 pdf/图片；Office 走 `previewStream`，其失败仍由第三方渲染器压成「PDF请求失败: 4xx」。已把 presign 前置校验扩展到**所有类型**（含 Office）以减少这类不可区分错误，该改动在本次构建之后完成，**尚未进包**，需下一次构建后复验。

### 2E. 最终确认轮（entry `index-CpE2zvYY.js`，md5 与 TL 核到的一致，13:37–13:47）

| 验收项 | 实际接口 | 状态 / CT | 页面层 | 证据 |
|---|---|---|---|---|
| ① 旅程4 问答抽屉 docx 引用 | `previewStream` | 200 / application/pdf | **PASS** canvas=1，1/1 111% | `final/RT-07-citation-open.png` |
| ② 详情页 pdf | `stream` | 200 / octet-stream | **PASS** canvas=1，1/1 124% | `final/PF-pdf-digital.pdf.png` |
| ② 详情页 docx | `previewStream` | 200 / application/pdf | **PASS** canvas=1，1/1 120% | `final/PF-docx-plain.docx.png` |
| ② 详情页 pptx | `previewStream` | 200 / application/pdf | **PASS** canvas=1，1/2 102% | `final/PF-R12FIX-product-intro.pptx.png` |
| ② 详情页 xlsx | `stream` | 200 / octet-stream | **PASS-with-note**（见下方三段 note） | `final/PF-R12FIX-credit-ledger.xlsx.png` |

**xlsx 的 note（三段，必须完整保留）**
- **形态**：当前为「表格文本渲染」（canvas=0，表头 + 4 行数据可读），接口走 `stream`。若后续改为 `previewStream` 并渲染成 PDF 分页，**属预期变化**（该链路本就是 Office→PDF），不改判 FAIL。
- **内容**：完整可读（列头「客户名称/所属产业链/信用评级/授信额度/已用额度/五级分类/到期日」+ 4 行记录，数值与原件一致）。
- **边界**：若产品要求「表格可筛选 / 可复制为表格 / 与原件版式一致」，此条应转 **“未实现”，不计 PASS** —— 本轮交付不具备表格交互能力，勿理解为已交付。
| ③ FAQ 启停失败可见性 | `PUT /faq/changeStatus` **注入 500** | 500 | **PASS**：toast「问答对禁用失败：服务不可用」，开关 `true→true` **不回落** | `final/FF-500.png` `final/faq-fail.log` |
| ④ global 双向 | `/qa/ai/question_re` | — | **PASS**（开 `1`+标识、关 `0`+无标识） | `final/RT-04` `final/RT-05` |
| 回归：KB 大小单位 / FAQ 启停(健康) / 提问有引用 | — | — | 均 **PASS** | `final/RETEST.log` |

**③ 的证据分级（不混淆）**
- **真实 500**（12:34，C 的 jar 被原地覆盖导致 `NoClassDefFoundError`）：当时实测「有提示 + 开关前后均 false」，属天然故障注入；
- **注入 500**（13:47，Playwright 拦截 `changeStatus` 返回 500）：验证前端失败可见性，**不冒充服务端故障**。
- 实际文案为「问答对禁用失败：<服务端 errorMsg>」；TL 提到的 `FAQ 列表加载失败，请检查服务是否可用` 属 FAQ **列表加载**分支的另一条文案，不是启停分支，两者不要混记。

## 1. 阻断级回归（单列，优先处置）

### F-D-01｜点引用打不开原文（403）— 已定位真因、前端已修、**已复测通过**（详见 §2E）

**现象（修复前，当前 dist）：** 问答回答下方「知识溯源 N」→ 展开引用卡 → 点 `R12FIX-product-intro.pptx` → 抽屉显示「加载失败 / PDF请求失败: 403」，控制台 `获取PDF stream数据失败`。
证据：`CITE-02-open-failed.png`、`CB-02-after-click.png`、`citation-body.log`。

**真因（与初判不同，已用抓包纠正）：**

1. 引用链路的真实请求是
   `POST /proxy/index/knowledgeBase/file/stream`
   body = `{"convertedFilePath":"/preview/convert?key=r12-rag%2Fkb_9%2F...pptx%2FV0%2F...pptx","pageNo":1,"pageSize":5}`
   —— **Office 文件被投给了 `stream`，而不是 `previewStream`**。
2. `KnowledgeBaseFileController.assertStreamAllowed()`（`rag-index-service.out:6627`）是"在键里找以 `kb_` 开头的段"做对象级授权；上面这个键把对象键 **URL 编码进了 query**，找不到 `kb_` 段 → 直接 `INSUFFICIENT_PERMISSIONS`（403/30016）。
3. 对照：知识库详情页的 `components/KnowledgeBaseZh/components/FileViewCom.tsx` 有正确分支（`usePreviewStream`），**只有问答抽屉 `AIChat/components/DrawerPreview.tsx` 漏了这条分支**。
4. 另需纠正一点：问答侧**从未真正 GET `/minio/`**；`/minio/` 只是给 stream 接口当键前缀。控制台那条 `/minio/...jpg` 403 来自 `pages/HomePage/IntelligentChat/AIChat/config/index.tsx:55` 写死的演示头像，与引用无关（但也确实是坏图，见 F-D-05）。

**已实施修复（未构建）：**

| 文件 | 改动 |
|---|---|
| `src/core/helps/fileAccess.ts`（新增） | `resolvePreviewTarget()`：Office→`previewStream`；图片→`GET /proxy/index/knowledgeBase/file/presign?key=`（带 `Authorization`）取短链直开；pdf/txt→鉴权 `stream`。presign 失败抛出服务端 `errorMsg`。 |
| `AIChat/components/DrawerPreview.tsx`（重写） | 改用上述解析；**失败显示「加载失败：<原因>」+「重试」**，同时 `message.error`；加载中显示「正在打开原文…」；不再静默。 |

**与 TL 契约的一处偏离（待裁决）：** PDF 仍走鉴权 `stream`，未改 presign。原因：渲染器对 pdf 是把**键** POST 给 `streamApiUrl` 取分页流；若传 presign 绝对 URL（带 query 签名），服务端 `normalizeObjectKey()` 会把签名当对象键的一部分 → 反而打不开。图片是 `<img src>` 直取，必须 presign，已改。

**验证状态：** 构建前无法验证（dist 未含新代码）。构建后需验 ①PDF 引用 ②Office 引用 ③无权限账号点引用被拒且有提示。

#### F-D-01 续：**"为什么 PDF 不用 presign 而用鉴权 stream"的证据**（TL 定稿口径的依据）

> TL 定稿：**取流一律传裸对象键** —— Office→`previewStream`，PDF/文本→`stream`，图片→`presign`。
> 下面这张表就是该口径的实测依据（admin 令牌直连 8088，排除前端变量）。

#### 三条链路的同一个病根（服务端不剥 `/minio` 前缀）

10:49–10:55 追加实测（用 admin 令牌直连 8088，排除前端变量）：

| 请求 | 结果 |
|---|---|
| `POST /file/stream`，`convertedFilePath=/minio/r12-rag/kb_9/pdf-digital.pdf/V0/pdf-digital.pdf` | **500** `getInputStreamByUrl failed` → `The specified key does not exist` |
| `POST /file/stream`，`convertedFilePath=r12-rag/kb_9/pdf-digital.pdf/V0/pdf-digital.pdf` | **200**，返回 `%PDF-1.4…` |
| `POST /file/stream`，`convertedFilePath=kb_9/pdf-digital.pdf/V0/pdf-digital.pdf` | **200**（两种裸键都行） |
| `POST /file/previewStream`，`convertedFilePath=/preview/convert?key=<urlencoded>` | **403/30016** |
| `POST /file/previewStream`，`convertedFilePath=r12-rag/kb_9/R12FIX-product-intro.pptx/V0/…pptx` | **200**，返回转换后 PDF |
| `GET /file/presign?key=r12-rag/kb_9/pdf-digital.pdf/V0/pdf-digital.pdf` | **401/30021「没有足够的权限」**（admin 也被拒） |

因此前端定稿为：**取流一律传裸对象键**（office→`previewStream`，pdf/txt→`stream`），**只有图片走 presign**。

**仍有一条前端改不了的**：问答里点**表格/文档引用**时，`@gientech/modual` 聊天库自己用 reference 元数据拼 `/minio/...` 去取 markdown，报「获取markdown数据失败: status 500」（服务端同一 `getInputStreamByUrl /minio/...` 失败，`rag-index-service.out:3463`）。该拼接在 `node_modules` 内，R13 规则禁止改，只能由服务端做归一化（见给 C 的建议：把 `normalizeObjectKey()` 应用到 `getInputStreamByUrl` 入参）。

---

## 2. 12 条旅程逐条状态

状态定义：**PASS**=从页面点通；**FAIL**=点不通/结果错误；**BLOCKED**=依赖能力缺陷无法进入；**NOT RUN**=未执行（附原因）。

| # | 旅程 | 状态 | 依据（页面实测） |
|---|---|---|---|
| 1 | 管理员建用户/部门/组，授予共享再撤权 | **NOT RUN（页面入口已验可用）** | 页面**可用**：`/system/organization/departments`「用户部门管理／新建部门／添加成员／批量导入导出／总人数 0」、`/groups`「分组管理／创建分组／未命名分组 成员人数 0」、`/roles` 有 3 个系统角色（超级管理员/管理员/普通用户）（`J4-_system_organization_departments.png` 等）。另「知识库 → 新建」弹窗可正常打开（`J6-03-create-kb-dialog.png`）。未执行原因：建用户/建组/授权/撤权均属真实写入，需与 C/F 的权限域用例对齐后统一做，避免与他们的夹具互相覆盖。 |
| 2 | 普通用户建库/目录、标签策略、批量上传全部格式 | **NOT RUN** | 同类原因（会新增知识库/文件并触发解析链路）。已知可用的页面入口：知识库列表「新建」、kb 详情「上传／新建文件夹／更多操作」。 |
| 3 | 查看成功/失败/重试及排队状态；打开原文/表格/图片/Office | **PASS（最终）** | 状态：知识解析/文件管理两页逐行显示状态（完成/解析中/失败）与「解析/重新解析」重试入口（`J3-01-file-manage.png`）。打开原文（构建后、独立浏览器上下文）：详情页 **4/4 内容可见**（pdf canvas 1/1、docx 1/1、pptx **1/2**、xlsx 表格文本完整，详见 §2E）；问答抽屉 Office **2/2 内容可见**（docx 1/1 111%、pptx 1/2 94%，均 `previewStream` 200 `application/pdf`）。早期 403（marker 投给 stream）与 500（`/minio` 前缀）均已修复并复测（§1 F-D-01）。图片引用未单独验（presign 现 200，仅接口层验证）。 |
| 4 | 语义改写提问、多轮追问、取消、重登录后历史恢复 | **多轮 PASS／历史 PASS／取消 FAIL（C09 未实现，非前端可解）／语义改写 NOT RUN** | 多轮：问「那信用方式最多能贷多少？」后端 `chat_history` 确实带上一轮（`rag-qa-service.out:387`），页面 7.6s 出答案（`J2b-04-followup.png`）。历史：`page.reload()` 后会话与问答仍在（`J2b-05-after-reload.png`）。取消：**流式中无任何停止/取消控件**——全量扫描 `button,[role=button]` 的 `innerText/aria-label/title`，无「停止/取消/stop/cancel」；流式中输入区只剩「新建对话/联网搜索/全局」3 按钮（`J2b-06-streaming.png`）。语义改写：需 LLM 侧改写入口，本轮未找到页面入口，未执行。 |
| 5 | FAQ 从抽取到编辑/启停/直答/删除 | **启停 PASS（正常/失败双分支）／抽取·编辑·删除 NOT RUN** | FAQ 管理页 10 条 Q/A、分页 1/2、每行启用/禁用开关（`J1-04-faq-manage.png`）。**正常分支**：健康时 `PUT /changeStatus` 200 且状态真实翻转（`final/RT-03`）。**失败分支**：真实 500（12:34 jar 被 `cp` 覆盖）与注入 500（13:52 / 13:54）均表现为「问答对启用/禁用失败：<服务端 errorMsg>」且 **开关不回落**（`final/FF-500.png`、`faq-fail.log`）。早期缺陷两层（`.then` 无 `.catch`；antd5 Switch 用 `value` 而非 `checked` 导致失控）已修复并复测通过。抽取/编辑/删除未执行（会改数据）。 |
| 6 | V0/V1 现行与历史差异问答 + 原版本引用 | **FAIL（入口不可达）** | 版本管理 Tab 只显示文件分组（如「R12FIX-product-loan」+ 新增文件/转移/解散/删除）与 分块数/解析方法/解析状态 列，**没有任何 V0/V1 版本标识或版本对比入口**（`J3-02-version.png`，页面全文无 "V0"/"V1"）。与 CHECKPOINT 记录的既有 FAIL「kb_9 无 V0/V1 共存（两条都是 V0）」一致。 |
| 7 | 表格筛选/聚合、数值单位、结构化只读查询、恶意查询拒绝 | **部分（表格查看 PASS／筛选未见入口／恶意拒绝 NOT RUN）** | 数据库页「数据库管理」有直连库 `r13-sql-guard-test`（MySQL 127.0.0.1:13306/gienrag）；数据表列表可见 `answer(321行/15列)`、`dialogue(307行/13列)`、`consolidated_balance(0行/24列)` 等（`J7-01-db-detail.png`）。点 `answer` 的「查看」→ `/chats/database/1/table/302709e8?...` 表头与列名正常渲染（`J8-01-table-data.png`），但**页面上没有筛选/搜索输入框**（未找到 placeholder 含"筛选/搜索/请输入"的控件）→ 筛选未通过页面验证。恶意 SQL 拒绝属服务端护栏，由 F/C 的用例覆盖，本轮未从页面验证。 |
| 8 | 图谱可视化/实体追溯/合并回滚/local 多跳 | **FAIL（无数据）** | kb_9「图谱增强」页显示「暂无数据」（表格 0 行，`J3-03-graph.png`）。页面本身可用（有「可视化图谱／图谱解析」子页签），但无图可看，旅程无法进行。 |
| 9 | global 跨文档/跨社区回答 + 每条结论原文回链 | **PASS（最终，双向）** | 缺陷期证据：`eventsEmit` 从不回调宿主（Playwright 序列化 `console.log("事件触发:",…)` 得 0 条），`chat.d.ts` 无 `onSenderConfigChange` ⇒ 开关只变视觉（`SP3-final.png`）。隔离验证：直接置 `localStorage.r13_global_mode=1` 后刷新 → 标识出现、请求体带 `"globalMode":true`、15.1s 返回带 1 条知识溯源（`global-bypass.log`）⇒ 后端链路本身正常。修复后（DOM 激活态注入，代码内含 `TODO` 与失效条件）：**开** → `localStorage=1` + 顶部标识 + 请求体带 `globalMode`；**关** → `0` + 无标识 + 不带（`final/RT-04`、`final/RT-05`）。 |
| 10 | 同名文档、更新/删除/重解析后检索与引用自动收敛 | **NOT RUN（他人正在做，我观察到并发影响）** | 10:44–10:46 kb_9 多文件被重解析；10:55 提问「智造贷最高额度」时答案变成「**8000万元**」（10:28 同问题是 5000 万元），我查 ES `kb_9` 索引：`最高授信额度为人民币5000万元` 与 `…8000万元` **两条同时存在**（对应 `R12FIX-product-loan.docx` 与 `R12FIX-product-loan(1).docx`）。即同名/更新文档的旧片段未收敛，问答可能取到新旧任一版本 —— 这属旅程 10 的收敛问题，需与 A/F 对齐其夹具时间点后再判定，**我不把它们算作本轮前端缺陷**。 |
| 11 | 无权账号/撤权/缓存与旧 session/直接访问/伪头/无效配置 负例 | **部分 PASS（页面级两条）／其余 NOT RUN** | PASS①：**未登录**直接访问 `/chats/knowledgeBase/9` → 被挡回 `/login`（`J6-01-noauth.png`）。PASS②：**伪造 token**（写入 localStorage 假 token + cookie）访问 `/chats/knowledgeBase` → `GET /proxy/auth/resource/getMenusByUser` 返回 **401**，页面回到 `/login`（`J6-02-forged-token.png`，接口序列见 `J6.log`）。未执行：无权账号（需第二个领域账号 + 撤权动作）、缓存/旧 session 复用、伪头（浏览器不可控）、无效配置。另注意：`/auth/user/kaptcha` 在该上下文出现 **500**，验证码接口本身不稳（已记 F-D-14）。 |
| 12 | 故障恢复、备份还原/升级回退后的相同旅程 | **NOT RUN** | 属 E/C 的恢复与回退动作，需其提供恢复后的时间点；本轮栈在 10:42 与 10:45 各发生一次服务退出，属"故障"而非"已验证恢复"。 |

---

## 2A. 构建后页面级复测（dist 入口 chunk `index-D1WCd56p.js`，2026-10-27 12:11）

| # | 项 | before | after | 证据 |
|---|---|---|---|---|
| 1 | KB 大小单位 | `大小：6717180M` | **PASS**（GB/MB 换算） | `before-build/RT-01-kb-list.png` → `RT-01-kb-list.png` |
| 2 | FAQ 启停 | 健康时 200 可用；失败路径无提示、开关不回落 | **PASS**（200 + 状态 true + 提示；失败路径已补 `.catch`） | `RT-03-faq-toggle.png` |
| 3 | 全局(GraphRAG) 双向 | 开/关都 `localStorage=0`、无标识 | **PASS**（开：`1`+标识出现；关：`0`+标识消失） | `RT-04-global-on.png` `RT-05-global-off.png` |
| 4 | 提问有引用 | PASS | **PASS**（知识溯源=1） | `RT-06-answer.png` |
| 5 | 引用打开原文 | 403 `PDF请求失败` | **链路 PASS（200）/ 内容部分 FAIL**：抽屉能开、`POST /file/stream` 200，但 xlsx 显示「无法解析为表格」 | `CM-R12FIX-credit-ledger.xlsx.png` |

**xlsx 那条的定性**：服务端 `previewStream` + xlsx → 200 转 PDF；`stream` + xlsx → 200 但返回 xlsx 原始字节，渲染器按"表格"分支解析二进制必然失败。已改：`xlsx/xls/csv` 纳入 `previewStream`，且凡走 previewStream 的目标以 `fileType="pdf"` 交给渲染器（待二次构建验证）。

## 2B. 部署陷阱（本轮实际踩到，影响所有"构建后验证"的可信度）

TL 12:01 替换 `frontend/plateform/dist` 后，18088 仍返回旧 chunk —— **bind mount 钉目录 inode**：宿主 `dist` inode=20194622，容器内 `/usr/share/nginx/html/rag` inode=19432113。换目录（mv/rsync 改名）后容器继续服务旧文件。处置：`docker restart r12-fe`（已做，3 秒）后生效。
→ 结论：**"改了 dist 没重启容器"会让任何"修复无效"的结论失真**，后续验证前必须先比对 `宿主 dist/index.html` 与 `curl 18088/index.html` 的入口 chunk 名（自检脚本已给 E）。

## 2C. 第二次构建后复测（entry `index-_Z7TjdPH.js`，2026-10-27 12:27）

| 项 | 结果 | 说明 |
|---|---|---|
| KB 大小单位 | **PASS** | 不再出现 `6717180M` |
| 全局(GraphRAG) 双向 | **PASS** | 开：`localStorage=1` + 顶部标识；关：`0` + 标识消失 |
| 提问有引用 | **PASS** | 知识溯源=1 |
| FAQ 启停 | **FAIL（服务端 jar 缺类）** | `PUT /index/faq/changeStatus` → 500，`NoClassDefFoundError: …FaqStatusUpdateReq$FaqStatusUpdateReqBuilder`。前端**已正确提示失败且开关不翻**——失败路径缺陷已闭合，但功能被服务端阻断 |
| 引用打开 docx | **FAIL（服务端匿名访问 MinIO）** | 前端已走 `previewStream`；服务端 `PdfUtils: 403 for http://127.0.0.1:19000/r12-rag/kb_9/docx-plain.docx/…`，Office 转 PDF 仍用匿名直连，R13 撤匿名读后必挂 |

**KB 详情页点文件的另一条结构性事实**：该预览由 `file-viewer-*.js`（`@mxmweb/fview`）渲染，**不经过 `GientechStreamReader`**，因此"把 13 个调用点收敛到包装器"覆盖不到它。它发出的仍是 `marker → /file/stream`（403/30016）。可解路径只有两条：①服务端 `assertStreamAllowed` 对 URL 编码键做一次 `URLDecoder` 兜底（C 已请示 TL）；②替换该第三方 viewer。**前端无法在不改 node_modules 的前提下修它**。

## 2D. 最终复测（entry `index-DZkCos_L.js`，12:33 构建；每项独立浏览器上下文）

**接口层（契约用例 `/tmp/r14_d/contract_preview_paths.py`）：15/15 PASS**

**KB 详情页"打开原文"四类 —— 页面层 4/4 可见内容**

| 文件 | 接口层（端点/状态/CT） | 页面层 | 证据 |
|---|---|---|---|
| pdf-digital.pdf | `200 / file/stream / application/pdf` | PASS，canvas=1，页码 1/1 | `final/KP2-pdf-digital.pdf.png` |
| docx-plain.docx | `200 / previewStream / application/pdf` | PASS，canvas=1，1/1 120% | `final/PF-docx-plain.docx.png` |
| R12FIX-product-intro.pptx | `200 / previewStream / application/pdf` | PASS，canvas=1，**1/2** 102% | `final/PF-R12FIX-product-intro.pptx.png` |
| R12FIX-credit-ledger.xlsx | `200 / file/stream / application/octet-stream` | PASS（形态不同）：表格文本渲染，表头+4 行完整可读，无 canvas | `final/PF-R12FIX-credit-ledger.xlsx.png` |

**4 项回归（12:44，已避开 E 声明的 10:42–12:17 作废窗口）**：KB 大小单位 PASS｜FAQ 启停 PASS（200 且状态真实翻转）｜全局(GraphRAG) 双向 PASS（开带 `globalMode`、关不带）｜提问有引用 PASS（知识溯源=2）。

**问答抽屉点引用（唯一未闭环）**：docx → `POST /file/stream` **500 参数非法**，抽屉「加载失败 / PDF请求失败: 500」。原因：本包尚未含"按源文件名后缀判类型"的修正，`getFileType(content, markerPath)` 返回空 → 落进 pdf 分支 → docx 被投给 stream。修正已就绪（`DrawerPreview.tsx` / `FileViewCom.tsx`），待下一次构建验证。

> **判定口径说明（避免假绿）**：以上每条都用**全新浏览器上下文**逐个验证（不共用页面），因为同一页面连续打开不同文件时，上一次的 viewer 会残留，`canvas>0` 会误判为成功——本轮一开始就踩过一次，已改成"一文件一会话 + 比对文件标题/页码"。

## 3. 可用性自查（TL 派工的第 1 项，逐步结果）

| 步骤 | 结果 | 证据 |
|---|---|---|
| 打开 `http://127.0.0.1:18088/` | PASS（302 → `/login`；登录后到 `/chats/main`，8 个一级菜单：智能对话/知识库/助手配置/敏感词配置/用户反馈/搜索/智能问答/系统管理） | `J1-01…`, `J2-00-main.png` |
| 知识库列表 | PASS（7 个知识库卡片，含 kb_9=R12验收主链 9 文件） | `J1-01-kb-list.png` |
| 进入 kb_9 | PASS（`/chats/knowledgeBase/9`，9 个 Tab：知识解析/FAQ/配置/检索测试/文件管理/版本管理/图谱增强/知识库配置/权限配置） | `J1-02-kb9-detail.png` |
| 文件列表 | PASS（10 行；解析完成 8、解析失败 1=pdf-encrypted.pdf、解析中 3（他人 10:46 重解析所致）） | `J3-01-file-manage.png` |
| FAQ Tab | PASS（FAQ管理/FAQ抽取） | `J1-03-faq-tab.png` |
| FAQ 管理页：有数据 | PASS（本页 10 条 Q/A） | `J1-04-faq-manage.png` |
| FAQ 管理页：分页 | PASS（1/2 页） | 同上 |
| FAQ 管理页：启停 | **FAIL**（假成功，见 F-D-02） | `J1-05-faq-toggle.png` |
| 每步页面报错文本 / 控制台 | 全程持续出现：`GET /proxy/qa/feedback/que/list` **500** + 未捕获 `AxiosError`；`GET /minio/dev-rag-data/header_pic/...jpg` **403** | 各 run log 的 digest 段 |

---

## 4. 缺陷清单（按严重度）

| 编号 | 缺陷 | 级别 | 归属 | 状态 |
|---|---|---|---|---|
| F-D-01 | 点引用打开 Office 原文 403（Office 走错 stream 分支，键被 URL 编码导致对象级授权失败） | 阻断 | 前端 | **已修并复测通过**：详情页 4/4 内容可见、问答抽屉 Office 2/2（均 previewStream 200/application/pdf），见 §2E |
| F-D-02 | FAQ 启停“假成功”：`.then` 无 `.catch`，5xx 不提示；antd5 `Switch` 用 `value` 而非 `checked`，失败后开关仍停在假状态 | 阻断（错误当成功） | 前端 | **已修并复测通过**：正常分支 200+真翻转；失败分支（真实 500 与注入 500）均出可读错误且开关不回落（`final/FF-500.png`）；对应 C10 |
| F-D-03 | 全局(GraphRAG) 开关点击不生效：库只做内部转发，不回调 `eventsEmit`；`onSenderConfigChange` 在 `chat.d.ts` 中不存在（死代码） | 阻断（旅程 9 不可达） | 前端 | **已修并双向复测通过**（方案 a，含 `TODO(R14-D-FIX-03)` 与失效条件）；后端链路另有隔离证据（见下注） |

> F-D-03 的隔离证据（证明不是后端问题）：把 `localStorage.r13_global_mode` 直接置 `"1"` 再刷新，页面出现「GraphRAG 全局」标识、`POST /qa/ai/question_re` 请求体带 `"globalMode":true`、15.1s 返回带 1 条知识溯源的答案（`G-01-tag-visible.png`、`G-02-global-answer.png`、`global-bypass.log`）。即 global 链路（注入→后端社区摘要→引用）本身通，断点只在"库不通知宿主"。
| F-D-04 | 检索服务不可用时**静默降级**：`retrieval_documents` 连接被拒 → 打 ERROR 后继续用 `documents:[]` 生成答案，页面无任何"检索失败"提示，且答案与知识库原文冲突（答"数千万元"，原文 5000 万），无引用 | 高（假成功/静默降级） | 服务端（C） | 已报 TL，待指派 |
| F-D-05 | 聊天页演示头像写死 `/minio/dev-rag-data/header_pic/...jpg`，R13 撤匿名读后每次 403（浏览器坏图 + 控制台报错） | 低 | 前端 | 仅记录（不在本轮改动范围） |
| F-D-06 | 知识库「大小」单位错：`fileTotalSize` 单位是 KB，界面直接后缀 `M` → kb_9 显示 `6717181M`（实为 6.4GB） | 低 | 前端 | **已修并复测通过**（`formatFileSize`，3 处）；对应 C02 |
| F-D-07 | `GET /proxy/qa/feedback/que/list` 每次进首页 500 + 未捕获 `AxiosError` | 中 | 服务端 | 已转 C；前端**不 catch**（错误必须可见） |
| F-D-08 | 流式回答无停止/取消控件 | 中（旅程 4 缺项） | 前端/依赖库 | 仅记录（需库支持 abort） |
| F-D-09 | 疑似同类单位问题：`VersionDetail/GraphBox/FolderDetail` 共 7 处 `fileSize` 直接拼 `MB`，单位基准未确认 | 低 | 前端 | 未改（怕误改），待确认单位后统一 |
| F-D-10 | `/auth/user/simpleLogin` 无验证码、无审计 | 高（安全） | 服务端 | 仅记录，建议进 C16 |
| F-D-11 | `GET /presign` 曾对 admin 返回 401/30021 | 高（图片引用打不开） | 服务端（网关接口表未登记） | **已修**：C 补 `interface_info`+`resource_interface`，现 presign 存在键 200、无法归属 403、不存在 404（契约用例 D1/E1 验证） |
| F-D-12 | 聊天库（`@gientech/modual`，不可改）自带拼 `/minio/...` 取 markdown → 表格/文档引用 500 | 高 | 服务端（C） | **已修**：C 在 `FileStorageUtils.getObjectNameFromUrl` 统一归一化，契约用例 A6（markdown+`/minio`）→ 200 |
| F-D-13 | `/file/stream`、`/previewStream`、markdown 三处不剥 `/minio` 前缀/不吃 URL 编码键 | 高 | 服务端（C） | **部分已修**：`/minio`、双桶名、绝对 URL、去桶名裸键全部 200（契约 15/15）；**URL 编码 marker 仍 403**（C 已批准下一次构建加 `URLDecoder` 兜底） |
| F-D-14 | `GET /auth/user/kaptcha` 在伪造 token 的页面上下文中返回 **500**（同一会话内另一次是 200），验证码接口不稳 | 中 | 服务端 | 仅记录（`J6.log` 接口序列） |
| F-D-15 | **技术债**：全局开关兜底依赖按钮 inline style 颜色（`rgb(78,110,242)`）判定——库若改主题色/改用 class，兜底立即失效且会"看起来点了没反应" | 中（技术债，已批准临时） | 前端 | 代码内已写 `TODO(R14-D-FIX-03)`：库补 `eventsEmit("sender:configChange")` 或正式 `onSenderConfigChange` 后**整段删除** |
| F-D-16 | E2 流式取消：`@gientech/modual` 发送区未暴露 abort 能力，src 层硬做会变成"点了停止但请求还在跑"的假功能 | C09 未实现项（FAIL） | 依赖库 | **非前端可解**：需换库/升级库；本轮按 FAIL 记录，不静默缩范围 |

---

## 5. 已改动文件（均在 `frontend/plateform/src/**`；未 git add / 未提交）

截至 12:50 共 **19 改 + 2 新增**：

**新增**
1. `core/helps/fileAccess.ts` —— 打开原文统一解析（Office→previewStream / 图片→presign / pdf→裸键 stream + presign 前置校验；错误按 403/404/5xx 三类文案）
2. `core/components/StreamReader.tsx` —— 包装库的 `GientechStreamReader`（同名导出），把历史 marker/`/minio`/图片直链三类错误输入统一收敛，失败显示原因 + 重试

**阻断级修复**
3. `AIChat/components/DrawerPreview.tsx`（重写：统一解析 + 失败可见 + 按源后缀判类型）
4. `KnowledgeBaseZh/components/FileViewCom.tsx`（同上）
5. `AIChat/index.tsx`（全局开关兜底，含 `TODO(R14-D-FIX-03)` 与失效条件说明）
6. `KnowledgeBaseZh/FAQ/FaqRow.tsx`（antd5 Switch `value`→`checked`）
7. `KnowledgeBaseZh/common/useFaqController.ts`（`changeStatus` 补 `.catch` + 错误提示）
8. `core/helps/index.ts`（新增 `formatFileSize`）+ `Detail.tsx` / `components/Card.tsx` / `components/KnowledgeBaseCard.tsx`（大小单位）

**统一入口的调用点（仅改一行 import，10 处）**
`KnowledgeAnalyBlock`、`KnowledgeAnalyGraph`、`SdqaDrawer`、`FileItem`、`KnowledgeSearch/ResultContentNew`、`RetrieveTest/ChatMessage`、`AIChat/components/DrawerContent`、`AiChat/components/ChatDisplayer/components/DrawerContent`、`AIChatComparison`、`Demo`。`main.tsx` 的 worker 注册**未动**。

类型检查：`npx tsc --noEmit` 全项目（排除 2026-01-21 既有脏文件 `index最新.tsx`/`index次新.tsx`）**476 行既有报错**，上述 21 个文件 **0 报错**。

**构建状态**：12:27（`index-_Z7TjdPH.js`）与 12:33（`index-DZkCos_L.js`）两版已包含第 1、2、6、7、8 项与多数调用点；**尚未包含**第 3、4 项的"按源后缀判类型"与 fileAccess 的 presign 前置校验（12:40 后完成），故问答抽屉 docx 引用仍 500。

### 5A. 「代码领先一版」清单（**未进当前包**，下一次构建会带）

当前线上包：`index-CpE2zvYY.js`（13:22 构建，含"按后缀判类型"+ 三类失败文案的 pdf/图片路径）。以下两处在**该构建之后**完成，`tsc` 干净、但**未进包**：

| 文件 | 改动 | 为什么没进包 | 影响（进包前一律记"未实现"，不记 PASS） |
|---|---|---|---|
| `core/helps/fileAccess.ts` | presign 前置校验从「pdf/图片」扩展到**所有类型（含 Office/表格）**；`403/404/5xx` 三类文案对 Office 也生效 | 13:22 构建后才改 | Office 引用失败时仍由第三方渲染器压成「PDF请求失败: 4xx」，**失败原因不可区分 = 未实现** |
| `core/components/StreamReader.tsx` | 包装器改为复用 `resolvePreviewTarget()`，消除"包装器一套、入口一套"的双解析漂移 | 同上 | 无用户可见变化（内部一致性/可维护性） |

**下一次构建窗口**：E 重打离线包时（TL 已确认暂不为这两处单独构建——理由是今日已 4 次构建、再构建收益小于风险）。届时用特征串复核：`grep -l "无权访问该原文" dist/assets/*.js` 命中即证明进包。

浏览器脚本未入库（避免与 F 的 `platform/r12/qa/**` 冲突），位于 `/tmp/dfe-r14/`（`lib.mjs` + `j1/j2b/j3/j4-system/j5-preview/j6-negative/j7-database/j8-table/citation-*/global-*`），可按需复制复核。

### 证据索引（`platform/r12/qa/evidence/R14-UI-20261027T022341Z/`）

| 主题 | 截图 | 日志 |
|---|---|---|
| 可用性自查（列表/详情/FAQ/分页/启停） | `J1-01-kb-list.png` `J1-02-kb9-detail.png` `J1-03-faq-tab.png` `J1-04-faq-manage.png` `J1-05-faq-toggle.png` | `J1.log` |
| 引用打开原文（失败基线） | `CITE-02-open-failed.png` `CB-02-after-click.png` | `citation-body.log` `citation-before.log` |
| 全局 GraphRAG 开关（不生效） | `SP3-final.png` `J2-04-global-on.png` | `switch-probe3.log` `global-switch-events.log` `global-event-payload.log` |
| 问答/多轮/刷新历史 | `J2b-01-answer.png` `J2b-04-followup.png` `J2b-05-after-reload.png` `J2b-06-streaming.png` | `J2b.log` |
| 文件/版本/图谱/检索测试 | `J3-01-file-manage.png` `J3-02-version.png` `J3-03-graph.png` `J3-04-retrieve-test.png` | `J3.log` |
| 知识库详情页原文预览（pdf 500） | `J5-01-pdf.png` | `J5.log` |
| 系统管理/组织页可用 | `J4-_system_organization_departments.png` 等 | `J4.log` |
| 权限负例（未登录/伪 token） | `J6-01-noauth.png` `J6-02-forged-token.png` `J6-03-create-kb-dialog.png` | `J6.log` |
| 数据库/数据表 | `J7-01-db-detail.png` `J8-01-table-data.png` | `J7.log` `J8.log` |

---

## 6. 环境事实（解释为何大量旅程停在"半路"）

| 时刻 | 事实 | 影响 |
|---|---|---|
| 10:20 开工 | 容器 `r12-fe` 处于 Exited(0)（10-27 01:59:59 优雅退出，`RestartPolicy=no`），18088 不可达 | 我用 `docker start r12-fe` 恢复，18088=200（已告知 E） |
| 10:26:48 | 19527（fulltext_es_api）连接被拒 → `PUT /index/faq/changeStatus` 500（`FAQAppServiceImpl:715`） | F-D-02 的触发条件 |
| 10:31–10:34 | `rag-index-service` 在 Nacos 掉注册 → qa 报 `Load balancer does not contain an instance for the service rag-index-service` | 两次提问走空 |
| 10:42:28 | `rag-index-service` 启动失败 `Failed to start bean 'webServerStartStop'` 后退出，18082 无监听、Nacos hosts 为空 | 知识库/FAQ/检索全阻断约 2 分钟 |
| 10:44:52 | 18082 恢复（pid 274832，Nacos healthy） | — |
| 10:45+ | `19995`（alg_retrieval_service）DOWN（`alg_retrieval_service.log` 末尾 `Finished server process`，未被拉起） | F-D-04（静默降级）；问答只剩纯 LLM 生成 |
| 10:44–10:46 | 他人对 kb_9 多文件触发重新解析（8 个文件在「解析中」） | 知识库数据同时在变，写操作类旅程不宜并行 |
| 11:01–11:17 | E 修改 `r12-java@` unit 类型时 `RemainAfterExit` 重复项导致 ExecStop 杀 JVM，**业务层含网关 8088 全断 16 分钟** | E 已声明该窗口内结果作废；本报告只采信 12:27 之后 |
| 11:47–12:17 | `rag-auth-service`(18081) 再停 30 分钟（同根因，E 做单点验证时踩到） | 同上作废窗口 |
| 13:39–13:45 | 一次全栈下线（8088/18082/18083 均无监听），成因见下一行 | 我的 xlsx 复测被打断，未记 FAIL，等恢复后重跑 |
| **13:50:02–13:50:58** | **A 用 `systemctl --user restart r12-alg.service` 重启了整个 alg 栈**。journal 佐证：13:50:02 Stopping → 19527 freed@13:50:03、19995 freed@13:50:25、19996 freed@13:50:46、13:50:49–58 四个服务依次 started（19526 pid1444586@13:50:45、19527 pid1444778@13:50:48、19996 pid1445565@13:50:54、19995 pid1451330@13:51:39）。A 首次公告误写"只重启 19527"，后自行更正 | 我 13:50:05 探到的三服务 DOWN **正落在 13:50:02–13:50:46 停止窗口内**，故属本次重启、非自发故障；`folder/list` 500 亦由此引起 |
| 13:51:36–13:54:05 | 19995 在 13:50:55 起过一版（pid 1445068，已退出），13:51:39 又起当前版（pid 1451330） | 我的 xlsx（13:51:36/13:53:33）与 FAQ 注入（13:52:07/13:54:05）**均落在第二次启动之后**，作为"恢复后验证"成立 |
| 13:53:33 / 13:54:05 | alg 栈全部 up 后重跑 xlsx 与 FAQ 注入两项 | 结论与恢复前一致：xlsx PASS-with-note；FAQ 注入 PASS。**两条结论均有"稳定窗口"内的时间戳** |

**结论：** 本轮能给出可信 PASS 的是"只读 + 单点交互"部分（且限定在 12:27 之后的稳定窗口、每项独立浏览器上下文）。凡涉及写入、跨版本、图谱、恢复的旅程，均已标 NOT RUN 并写明原因，未用环境窗口内的数据充数。

> **一条方法论教训（本人）**：13:50 我观察到 alg 服务 DOWN 并写进报告时，只描述了"现象+时刻"，没有先确认"是否有人在重启"。事后 A 更正才知道是 unit 级重启。**正确做法：异常出现时先查进程/公告（谁在动服务），再定性"故障"或"人为窗口"**——否则会把人为操作写成系统不稳定。
