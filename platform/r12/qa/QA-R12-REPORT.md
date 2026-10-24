# R12 功能验收与安全复核报告（内部独立复核）

- 复核角色：qa-reviewer（**未参与 R12 任何实现**，Java/Python/前端/模型均由他人完成）
- 复核性质：**内部独立复核，非外部签署**。本报告不构成生产放行意见，也不替代 Owner 批准。
- 复核时间：2026-10-24/25（UTC 证据时间戳见下）
- 被测环境：`platform/r12`（网关 127.0.0.1:8088 为唯一对外入口）
- 复核脚本（QA 自写，**未 import** 开发自检脚本）：`platform/r12/qa/qa_suite/`
  - `client.py` 独立客户端（记录每次请求的 header 键 / payload 字段，用于检查"不提交正文"这类承诺）
  - `negatives.py` 断言库（纯函数，可被喂假观察重新求值）
  - `suite.py` 场景驱动（S1~S8）
  - `mutate.py` 变异自检（证明断言非空转）
  - `fixtures.py` 第二用户夹具（明确标注为测试夹具）

---

## 0. 一句话结论

**本轮不能判"功能验收通过"。** 主链在"建库→上传"这一步就断了（`errorCode=7009 模型类型不能为空`），
上传/解析/问答/引用/历史五个场景无法进入有效判定（BLOCKED）；
与此同时，权限与安全侧发现 **2 项高严重度缺陷**（网关白名单有 4 个业务端点未授权可达，其中 1 个会把完整 SQL 与表结构回给未认证调用方）。

| 结论口径 | 计数 |
|---|---|
| PASS（有正向对照、断言经变异验证） | 11 |
| FAIL（系统侧不满足验收点） | 8 |
| BLOCKED（依赖未就绪，无法形成有效判定） | 8 |
| 合计 | 27 |

> 计数口径说明：按"用例"计（同一场景可能有多个用例），取自本报告第 3 节表格：
> PASS = S1×3 + S2×1 + N1 + N3 + N4 + N5b + S9×3；FAIL = S3×5 + N2 + N6 + S9(重复会话)；
> BLOCKED = S4 + S5 + S6 + S7(历史含回答) + N5 + N7 + N8 + N9。
> 所有 FAIL/BLOCKED 均可由第 4 节证据目录内的 JSON 逐条复现。

**本轮功能验收状态：未通过（阻塞于 D-01），安全侧 2 项高危待修（D-02/D-03）。**

**不代表生产可发布**：本轮未做压测、容量、故障注入、数据迁移、备份恢复、审计留存与合规检查；
模型/解析服务的资源占用、并发下的索引一致性、以及 `docs/policies/**` 要求的发布前置项均未覆盖。

---

## 1. 环境就绪度（事实，实测）

| 依赖 | 端口 | 状态（2026-10-25 04:5x UTC 实测） |
|---|---|---|
| 网关 | 8088 | OPEN |
| Java auth/index/qa/sensitive | 18081/18082/18083/18085 | OPEN |
| MySQL / Redis / ES / Milvus / MinIO | 13306/16379/19200/19630/19000 | OPEN |
| 模型 embedding/rerank/LLM/VLM | 18090/18091/18092/18093 | OPEN |
| doc-parse | 12340 | OPEN |
| ES 代理 | 19527 | **反复启停**（一次探测 OPEN，随后又 closed） |
| Milvus 代理 | 19526 | closed |
| 算法检索 | 19995 | closed |
| LLM 编排 | 19996 | closed |
| `model_info` 表 | — | **0 行**（模型未登记） |

结论：**模型推理进程在跑，但模型未在产品内登记，且检索/编排服务未就绪** → 问答链路无法形成端到端证据。

---

## 2. 缺陷清单（按严重度）

### D-01【阻塞 / 功能】建库→上传链路必然失败：`7009 模型类型不能为空`
- 现象：`POST /index/knowledgeBase/file/uploadFileList`，PDF/DOCX/XLSX/PPTX/PNG **全部**返回
  `http=500 {"errorCode":"7009","errorMsg":"模型类型不能为空"}`。
- 根因（代码 + 数据两侧同时成立）：
  1. `KnowledgeBaseListAppServiceImpl:982` 上传前调用 `modelInfoAppService.getSimpByModeName(kb.getModelName())`；
     `ModelInfoAppServiceImpl:394` 对空 `modelName` 直接抛 `MODEL_TYPE_IS_NULL(7009)`。
  2. 建库请求里传了 `embeddingModelName=bge-m3`，但落库 `knowledge_base.config` 只有
     `{"fileFaqMaxNums","similarQuestionMaxNums","chunkSize","chunkOverlap","fileType"}` —— **没有 modelName**。
  3. `model_info` 表 **0 行**，`platform/r12/seed/seed_models.py` 未执行（该脚本至今未被运行）。
- 影响：S3/S4/S5/S6/S7 全部无法进入；坏文件负例被"环境错误"挡住而**不能算通过**（见 N7/N8 的 BLOCKED）。
- 修复去向（不由 QA 执行）：①执行模型登记种子；②确认建库→上传之间 `modelName` 的权威来源
  （是建库时持久化，还是上传时显式传？）——这一条不明确，即使登记了模型，新建库仍会 7009。
- 证据：`evidence/20261024T204512Z-up1/{results.json,summary.md}`

### D-02【高 / 安全】网关白名单内 4 个业务端点未授权可达，并外泄完整 SQL 与表结构
- 源码事实：`services/rag-java/.../rag-gateway/.../filter/AuthFilter.java:76-93` 的 `noTokenPaths` 用
  `path.startsWith(prefix)` 前缀匹配放行；其中 4 条命中真实业务端点：
  `/index/knowledgeBase/file/list`、`/index/knowledgeBase/file/multiple/version`、
  `/index/parseTask/callback`、`/index/knowledgeBase/file/uploadParsedFile`。
- 实测（**未携带任何凭证**，全部不是 401）：

  | 端点 | 方法 | 实测 | 说明 |
  |---|---|---|---|
  | `/index/knowledgeBase/file/list?kbId=1&type=1` | GET | 500 `Cannot parse null string` | 已进入业务层（因无用户上下文而 NPE） |
  | `/index/knowledgeBase/file/multiple/version?kbId=1&type=1` | GET | 500 **回显完整 SQL** | 见下方摘录 |
  | `/index/parseTask/callback` | POST | 500 `... getRetryTimes() because "task" is null` | 回调业务已执行，伪造 taskId 即可打到 |
  | `/index/knowledgeBase/file/uploadParsedFile?kbId=1&fileId=1&userId=1` | POST | 500 `知识库文件不存在(10002)` | **业务级校验已通过鉴权关**，属未认证写入面 |

- 被外泄的内容（未认证调用方直接拿到）：
  ```
  ### The error may exist in com/gientech/ragindexservice/domain/mapper/KnowledgeBaseMapper.java
  ### SQL: SELECT id,kb_name,primitive_name,kb_type,kb_des,source_url,status,config,kb_label,
                  create_by,gmt_create,modify_by,gmt_modified,platform,private_kb FROM knowledge_base
         WHERE (primitive_name IN () AND status = ?)
  ```
  即：**表名、全部列名、mapper 类名、SQL 形态**。这属于信息泄露，可直接用于后续攻击面构造。
- 危害推演（标注为判断，非事实）：`parseTask/callback` 与 `uploadParsedFile` 是"解析结果回写"入口，
  未授权可达意味着可对已存在文件伪造解析完成/替换解析内容 → **索引投毒**（当前因无文件数据未能实测到写入成功）。
- 证据：`evidence/20261024T204628Z-neg3/s8_negative_obs.json` 的 `N6`
- 附带事实：`noTokenPaths` 里还有 `/index/knowledgeBase/file/list`、`/graph/search/ping`、
  `/index/knowledgeBase/file/multiple/version` 等"内网调用"语义的路径 —— 但它们挂在**对外网关** 8088 上，
  与 `R12-ENV-CONTRACT.md` A-10 的"内部代理"定位冲突。

### D-03【中 / 健壮性】非法格式 token 返回 500，而非规范化的 401
- 实测：`Authorization: Bearer <64位hex>` → `http=500`（Spring 默认错误体）。
- 机制：`AuthFilter:178` 用 `JWTUtils.getUsername(token)` 解未校验格式的 token，异常未被捕获。
- 影响：不是放行（未造成越权），但把"拒绝"变成了 5xx，破坏可观测性与客户端处理；
  本轮响应体已确认**未**包含堆栈（属可控范围，故降级为中）。
- 正向对照：`alg=none`、伪签名 两种 JWT 均被 401 正确拒绝 —— 拒绝能力本身存在。
- 证据：`evidence/20261024T204628Z-neg3/s8_negative_obs.json` 的 `N2`

### D-04【中 / 安全，代码事实 + 未实测】知识库文件读取无属主/权限校验（IDOR 面）
- 代码事实：`KnowledgeBaseListAppServiceImpl:829 getFileChunksByPage(kbId, docId, ...)` 只校验 kb/doc 是否存在与解析状态，
  **没有任何** `create_by == 当前用户` 或 `private_kb` 判定；`KnowledgeBaseFileController:89 /list` 的实现同样不含属主条件。
  权限体系（`AuthenticateAppServiceImpl`）**只做 URL 级授权**（path+method 对 `interface_info`），没有数据级 ACL。
- 运行时：本轮**未能实测到泄露**——私有库 `kbId=3` 无文件（上传被 D-01 阻断），非属主读到的是 0 条；
  按断言口径记 BLOCKED 而不是 PASS，避免"0 条即被过滤"的误判。
- 复测条件：D-01 修复后，在私有库放入 1 个已解析文件，用 `qa_user_b` 读 `getFileChunks` / `file/list`。

### D-05【中 / 正确性，代码事实 + 实测未复现】`AuthFilter.filter()` 内两次 `chain.filter()`
- 代码：`AuthFilter.java:194-206` —— `return chain.filter(exchange).then(Mono.defer(() -> { ...; return chain.filter(finalExchange); }))`，
  链被订阅两次。
- 实测尝试：同样一次 `POST /index/knowledgeBase/create` 只产生 1 条记录（无重复入库），
  故**不下结论"必然重复执行"**，只登记为可疑代码，需维护方确认（尤其对写接口）。
- 证据：`mysql: select kb_name,count(*) from knowledge_base group by kb_name` → 三个库各 1 条。

### D-06【低 / 安全】JWT 签名密钥硬编码在源码
- `rag-common/.../utils/JWTUtils.java:22`：`private static final String signature = "signature-gien-rag";`
- 缓解（实测有效）：网关除了验签，还要求 `token.equals(redis[user:token:<userName>])`（`AuthFilter:178-183`），
  所以"用硬编码密钥自签 admin token"不能直接冒用身份（我用 `qa_user_c` 的 token 改 payload 为 admin，被判 401）。
- 风险仍在：密钥随源码扩散、无法按环境轮换；且给了攻击者离线构造"格式合法"token 的能力。

### D-07【中 / 一致性】模型不存在时把错误信息当作"答案"写入对话历史
- `AiServiceImpl:341-345`：`catch (ApplicationException)` 且 code=MODEL_NOT_EXIST 时，
  `addQuestionAndAnswerRe(...)` 把 `e.getMessage()` 作为答案入库并作为回复下发，`resultType=SENSITIVE_WORDS`。
- 影响：失败被"记录成一次成功的问答"，后续历史恢复与统计会把错误当业务数据。

### D-08【中 / 前端】写作模块 mock 开关硬编码为 `true`
- `frontend/plateform/src/components/Template/index.tsx:96`：`serverInfo` 初始值 `enableMock: true`；
  `components/AiEditor/core/services/servers.ts:101-133` 据此装 `axios-mock-adapter`，接口直接回 mock 数据，
  且 `catch` 的"获取引用文件失败"提示被注释掉。
- 影响范围：`pages/HomePage/Writing/EditTemplate`（写作/模板）；**不在 RAG 对话主链**上，故未影响 S1~S8。
- 另：`AIChat/mocks/chat_reference_mock.ts` 等 mock 文件仅被 `mocks/index.ts` 内部引用，未进入生产引用链（已核）。

### D-09【低 / 配置】生产 profile 打着 dev 标签
- `frontend/plateform/.env.production` 内容与 `.env.development` 一致（`VITE_ENV= dev`），
  生产构建无法从环境标签区分；`VITE_CONFIG_SHOW_DATABASE=true` 也在生产开启。

### 已核实"不是缺陷"的两条（记录以免下轮重复怀疑）
- 登录响应**不**回显口令/哈希：响应里 `userPassword` 字段存在但值为 `null`（`S1` 用例断言覆盖）。
- `/index/knowledgeBase` 未授权访问返回的是 `401 没有token(30022)`，规范化拒绝成立（`N1` 有正向对照 `200`）。

---

## 3. 逐场景结果（输入 / 预期 / 实际 / 证据）

> 证据根目录：`platform/r12/qa/evidence/`

### S1 登录与身份 —— PASS（3/3）
| 用例 | 输入 | 预期 | 实际 | 证据 |
|---|---|---|---|---|
| 取菜单 | `GET /auth/resource/getMenusByUser`（admin） | 200 且菜单非空 | 200，7 个菜单 | `20261024T204507Z-probe1/results.json` |
| 取身份 | `GET /auth/user/getUserInfo` | userName=admin | 是 | 同上 |
| 口令不回显 | `POST /auth/user/simpleLogin` | 响应不含明文/哈希 | `userPassword=null` | 同上 |

### S2 建库 —— PASS（1/1）
`POST /index/knowledgeBase/create {"kbName":"R12-QA-独立复核库",...,"embeddingModelName":"bge-m3"}`
→ 200，`kbId=2`，`primitiveName=kb_2`。
**但**落库 config 缺 `modelName`，直接导致 D-01（建库用例通过、上传用例失败，两者并列呈现，不互相掩盖）。

### S3 上传 5 类文件 —— FAIL（5/5）
| 输入 | 预期 | 实际 |
|---|---|---|
| `pdf-digital.pdf` | 200 + fileId | 500 `7009 模型类型不能为空` |
| `docx-table.docx` | 同上 | 同上 |
| `table-ledger.xlsx` | 同上 | 同上 |
| `image-slide.pptx` | 同上 | 同上 |
| `scan-text.png` | 同上 | 同上 |

证据：`20261024T204512Z-up1/results.json`

### S4 解析状态 + chunk 落地 —— BLOCKED
无成功上传的 fileId，`getFileStatusById`/`getFileChunks` 无从校验。
断言已就绪且经变异验证（`P3 解析成功必须真的有内容`：注入 `status=3, chunk=0` 会判 FAIL），等 D-01 修复即可执行。

### S5 换措辞提问 → 真实模型回答 —— BLOCKED
`/qa/ai/question_re` 的上游 19995/19996 均未就绪（closed），且库内无已解析文件。
断言已就绪：答案长度、引用非空、**两种措辞命中文件集合交集非空**（语义检索证据，而非日志自证）。

### S6 引用一致性 + 不提交正文 —— BLOCKED
断言已就绪并经变异验证：
- `P1`：引用 `file_id` 必须属于本库已上传文件（注入 `999999` → FAIL）
- `P2`：提问 payload 字段 ⊆ 白名单且 `content` 长度≈问题长度（注入 `fileContent` 字段 → FAIL）
- 关键要素覆盖率 ≥0.6（中文 2-gram + ASCII 词，不做整句匹配）与 `page_number` 合法区间。

### S7 历史对话恢复 —— BLOCKED
`GET /qa/dialogue/list` 可返回 200/空列表；`getDialogBySessionId` 无可恢复的对话内容（S5 未产生）。

### S8 负例 —— 7 用例：PASS 5 / FAIL 2 / BLOCKED 2
| 用例 | 预期 | 实际 | 结论 |
|---|---|---|---|
| N1 无 token | 401/403，且带 token 同请求 200 | 401 `没有token`；对照 200 | **PASS** |
| N2 伪造 JWT | 全部 401/403 | `alg=none`→401、伪签名→401、非 JWT 垃圾串→**500** | **FAIL**（D-03） |
| N3 篡改 payload（`qa_user_c`→admin，保留原签名） | 401 且不泄露 admin 数据 | 401 `登录失效已过`，无泄露 | **PASS** |
| N4 注销后旧 token 复用 | 401/403 | 401 | **PASS** |
| N5 越权读他人私有库 | 403/业务拒绝 | 200 但 0 条（库内无文件） | **BLOCKED**（不判 PASS） |
| N5b 按 fileId 直读他人文件 | 不得返回数据 | 200 且 `data=null` | **PASS** |
| N6 网关白名单未授权可达 | 401/403 | 4 个端点全部 5xx 进入业务层，1 个回显完整 SQL | **FAIL**（D-02） |
| N7 坏文件（随机字节 .pdf） | 明确失败 | 500 `7009`（**拒绝原因与被测目标无关**） | **BLOCKED**（防空转） |
| N8 扩展名伪装（文本改 .pdf） | 明确失败 | 同上 | **BLOCKED**（防空转） |
| N9 删除文档后再提问不得再引用 | 引用不含被删 file_id | 无文件可删 | **BLOCKED** |

证据：`20261024T204628Z-neg3/{results.json,s8_negative_obs.json}`

> N7/N8 的处理是本轮最关键的方法论判断：它们**表面上会 PASS**（确实返回了非 2xx），
> 但拒绝原因是环境缺陷 7009，不是"识别出这是个坏文件"。若照抄这个 PASS，就是典型空转。
> 断言里已内置 `env_blocked` 守卫，把这类情况强制降为 BLOCKED。

---

## 4. 变异自检（证明断言不是空转）

`python3 qa_suite/mutate.py` → 证据 `platform/r12/qa/evidence/mutation-selfcheck.json`

做法：对每条断言，把真实观察里的关键字段改成"违约值"再喂回同一函数，要求必须翻成 FAIL；
若注入违约值后仍 PASS/BLOCKED，即判空转。

| 用例 | 基线 | 注入违约后 | 结论 |
|---|---|---|---|
| N1 无 token | PASS | FAIL（status→200） | 非空转 |
| N2 伪造 token | FAIL | FAIL（伪造→200） | 非空转 |
| N3 篡改 payload | PASS | FAIL（leaked_admin=true） | 非空转 |
| N4 注销后复用 | PASS | FAIL（status→200） | 非空转 |
| N5 越权 | BLOCKED | FAIL（非属主读到 3 条） | 非空转 |
| N6 白名单 | FAIL | FAIL（callback→500） | 非空转 |
| N7/N8 坏文件 | BLOCKED | FAIL（status=3, chunk=0 静默成功） | 非空转 |
| N9 删除后引用 | PASS | FAIL（被删 file_id 仍在引用） | 非空转 |
| P1 引用归属 | PASS | FAIL（引用 999999） | 非空转 |
| P2 不提交正文 | PASS | FAIL（出现 fileContent 字段） | 非空转 |
| P3 成功必须有内容 | PASS | FAIL（status=3, chunk=0） | 非空转 |

**12/12 条断言在注入违约观察后均翻成 FAIL。**

---

## 5. 对开发自检脚本 `acceptance.py` 的断言强度审查（属我职责，逐条点名）

| # | 位置 | 问题 | 后果 |
|---|---|---|---|
| 1 | `s8()`「坏文件上传被明确处理」 | `record(..., True, ...)` —— **结论参数硬编码 True** | 无论服务端返回什么（含成功入库）都 PASS，100% 空转 |
| 2 | `s3()` 加密 PDF 负例 | 只判 `code!=200 or not success`，无"合法文件此刻应成功"的对照 | 本环境全部上传因 7009 失败 → 负例必然 PASS（本轮已实测复现） |
| 3 | `s6()`「引用携带文件与定位信息」 | 只要求 refs 里存在 `metadata.source` 字段 | 引用指向任意别的文件/版本仍 PASS，无法验证"定位到正确位置" |
| 4 | `s6()`「不随请求传正文」 | 用例名这么写，但只验证服务端能取回 chunk，**没有检查实际发出的 payload** | 承诺未被证伪也未证实 |
| 5 | `s5()` | 只判 `len(answer)>10` | 模型胡说八道、答案与引用无关都 PASS |
| 6 | `s4()` | 只判 `status==3` | "状态成功但 chunk=0"的静默成功不会被发现 |
| 7 | `s8()` 越权 | 实际测的是"删除不存在的知识库" | 完全没有覆盖"用 A 用户访问不属于他的库" |
| 8 | `s8()` token 负例 | 只测 1 个 GET，无正向对照 | 端点整体失效时也会被当成"权限生效" |
| 9 | 全局 | 无变异自检 | 无法排除空转 |

建议由原作者按下表最小修改：所有"必须失败"的用例都要带正向对照；所有"成功"的用例都要有内容级校验；
每个负例至少跑一次期望反转。

---

## 6. 复测触发条件（等这两件事之一完成我就继续）

1. `model_info` 完成登记 **且** 新建知识库能拿到 `modelName`（需明确来源）→ 解除 S3/S4，随后 S5/S6/S7/N5/N7/N8/N9。
2. 19526/19527/19995/19996 全部稳定 OPEN → 解除 S5/S6 与检索侧证据。

每 3–5 分钟复查一次端口与 `model_info` 行数，不空等。

---

## 7. 本轮边界声明

- 我未修改 `services/**`、`frontend/**`、`platform/r12/conf/**`、`platform/r12/nacos/**` 的任何文件；
  产物仅落在 `platform/r12/qa/**`。
- 我新建了 **2 个测试夹具用户**（`qa_user_b` role=2、`qa_user_c` role=3，口令不入库明文、不入报告）与 3 个测试知识库，
  用于越权对照。清理 SQL 见 `qa_suite/fixtures.py` 输出，**不自动执行**（执行会销毁本轮证据）。
- 报告中**事实 / 推断 / 判断**已分别标注：标"实测"的均为本报告脚本产生；
  标"代码事实"的为源码可验证但运行时未复现；标"判断/推演"的为我基于前两者的推理，不作为验收结论依据。
- 我**没有**以外部独立 QA 身份签署任何内容，也**没有**替 Owner 做生产批准。
