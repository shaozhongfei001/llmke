# R12 功能验收与安全复核报告（内部独立复核）

- 复核角色：qa-reviewer（**未参与 R12 任何实现**；Java/Python/前端/模型均由他人完成）
- 复核性质：**内部独立复核，非外部签署**。本报告不构成生产放行意见，也不替代 Owner 批准。
- 复核时间：2026-10-25（UTC；各证据目录时间戳见正文）
- 被测环境：`platform/r12`，网关 `127.0.0.1:8088` 为唯一对外入口
- 复核脚本（QA 自写，**未 import** 开发自检脚本）：`platform/r12/qa/qa_suite/`
  - `client.py` 独立客户端（逐条记录实际发出的 header 键 / payload 字段，用于检查"不提交正文"这类承诺）
  - `negatives.py` 断言库（纯函数，可被喂假观察重新求值）
  - `suite.py` 场景驱动（S1~S9）
  - `mutate.py` 变异自检（证明断言非空转）
  - `fixtures.py` 第二用户夹具（明确标注为测试夹具）

---

## 0. 结论

**本轮功能验收不通过。** 主链已能跑通到"建库 → 上传 5 类文件 → 解析 → 真实模型回答 → 历史恢复"，
**检索能力本身也已验证为真**（ES+Milvus 混合召回 + rerank，换措辞命中同一批 file_id）。
但**本轮最重要的验收点「答案 → 引用 → 点击引用定位到原文」不成立，且是三处独立断点叠加**：
① 引用恒为空（D-12：Java 侧确认已收到 4 条检索文档，但引用装配与前端二次过滤**都以"模型在正文输出引用标记"为前提**，
   模型本轮未输出 → 两侧一致清空，答案照常返回、不标降级）；
② 引用地址被前端拼成内网 `10.15.12.13:9000`，且 MinIO 匿名 403（D-15）；
③ 后端 `viewFile` 只接受绝对 URL，且匿名取私有桶 403（D-16；其"类加载 500"已由干净重启消除）。
任一处单独修复都不足以让该验收点通过。

安全侧本轮**实测确认 1 项数据级越权（读写双越权）**：非属主用户 `qa_user_b` 成功读取了 admin 私有知识库的文件**及其正文 chunk**，
并**成功删除**了 admin 的文件（DELETE 返回 `success=true`）
（D-04，证据 `qa/evidence/N5-idor-proof.json`、`qa/evidence/D04-idor-variants.json`），并叠加未授权可达的解析回写端点（D-02）。

| 结论口径 | 计数 |
|---|---|
| PASS | 32 |
| FAIL | 9 |
| BLOCKED | 3 |
| 合计 | 44 |

> 计数口径：按"用例"计，明细见第 3 节。
> PASS = S1×3 + S2×2 + S3×5 + S4×4 + S5×3(两次回答 + 检索机制) + S6×1 + S7×3 + S9×3
>        + (N1,N3,N4,N5b,N7,N8)×6 + (列表层不越权暴露)×2；
> FAIL = S4(PPTX)×1 + S5(引用)×2 + S6c(引用预览取原文)×1 + S9(重复会话)×1
>        + N2 + N5(读越权) + N5c(写越权) + N6；
> BLOCKED = S6(引用归属) + S6(引用支撑) + N9（三者均被 D-12 阻断）。

**本轮功能验收状态：不通过（阻断于 D-12 引用缺失）。**
**不代表生产可发布**：本轮未做压测、容量、故障注入、数据迁移、备份恢复、审计留存与合规检查；
索引一致性、并发写入、`docs/policies/**` 的发布前置项均未覆盖。

---

## 1. 环境事实（实测）

| 依赖 | 端口 | 状态 |
|---|---|---|
| 网关 | 8088 | OPEN（**复核期间多次 503/连接拒绝**，见 §6 环境稳定性） |
| Java index/qa/auth/sensitive | 18082/18083/18081/18085 | OPEN（期间多次重启） |
| Redis/ES/Milvus/MinIO/MySQL | 16379/19200/19630/19000/13306 | OPEN |
| 模型 embedding/rerank/LLM/VLM | 18090/18091/18092/18093 | OPEN |
| 检索/ES 代理/Milvus 代理/LLM 编排 | 19995/19527/19526/19996 | OPEN（复核开始时不就绪，后由 alg-ops 交付） |
| `model_info` | — | 4 行，`status=1`（TL 已执行 seed；我复核通过） |
| ES 索引 `kb_5` | — | `_count=5`（按 `count(*)` 校验，未用 `num_entities`） |

---

## 2. 缺陷清单

### D-01【已解除 / 功能】建库→上传 `7009 模型类型不能为空` —— **已修复，我复核通过**
- 早期实测：5 类文件上传全部 `500 7009`；`model_info` 为 0 行，且 `knowledge_base.config` 缺 `modelName`。
- 修复后复核（事实）：`model_info` 4 行且 `status=1`；删除旧库后新建 `qa_r12_indep`（kbId=5），
  `getKbById` 返回 `embeddingModelName=bge-m3 / modelName=qwen2.5-7b-instruct / multiModelName=qwen2.5-vl-3b-instruct / faqModelName=qwen2.5-7b-instruct` 四项齐全；
  随后 5 类文件上传全部 200。
- 保留记录：TL 登记的 R12-FIX-KB-01（`checkEmbeddingModelChangeAndSendMsg` 对 `originalEmbeddingName` 无空判断 → 旧库不可通过 `updateConf` 修复）与我的观察一致，属真实缺陷。
- 证据：`evidence/20261024T212542Z-full1/results.json`

### D-02【高 / 安全，**未修复**】网关白名单内 4 个业务端点未授权可达，并外泄完整 SQL 与表结构
- 源码：`AuthFilter.java:76-93` 的 `noTokenPaths` 用 `path.startsWith(prefix)` 放行，其中 4 条命中真实业务端点。
- **面（未授权可达）**（实测，均非 401）：

  | 端点 | 方法 | 实测 |
  |---|---|---|
  | `/index/knowledgeBase/file/list` | GET | 500 `Cannot parse null string`（已进入业务层） |
  | `/index/knowledgeBase/file/multiple/version` | GET | 500 **回显完整 SQL + 表名 + 全部列名 + mapper 类名** |
  | `/index/parseTask/callback` | POST | 500 `getRetryTimes() because "task" is null`（回调业务已执行） |
  | `/index/knowledgeBase/file/uploadParsedFile` | POST | 500 `知识库不存在(10002)`（已过鉴权关，进入业务校验） |

- **已造成后果**：仅确认**信息泄露**（下述 SQL 文本）。**未确认**任何未授权成功写入/投毒：
  `parseTask/callback` 与 `uploadParsedFile` 需要合法 taskId/fileId，本轮未构造出成功的未授权写入，
  故只报"攻击面"，不报"已投毒"。
  ```
  ### The error may exist in .../domain/mapper/KnowledgeBaseMapper.java
  ### SQL: SELECT id,kb_name,primitive_name,kb_type,kb_des,source_url,status,config,kb_label,
                  create_by,gmt_create,modify_by,gmt_modified,platform,private_kb FROM knowledge_base
         WHERE (primitive_name IN () AND status = ?)
  ```
- 证据：`evidence/20261024T213354Z-neg4/s8_negative_obs.json` 的 `N6`

### D-03【中 / 错误码语义，未修复】非法格式 token 返回 500 而非规范化 401
- `AuthFilter:178` 用 `JWTUtils.getUsername(token)` 直接解未校验格式的 token，异常未捕获。
- 实测：`alg=none`→401、伪签名→401、**非 JWT 垃圾串→500**（Spring 默认错误体，未含堆栈）。
- 归属：TL 记为 R12-FIX-AUTH-01。
- 证据：`evidence/20261024T213354Z-neg4/s8_negative_obs.json` 的 `N2`

### D-04【严重 / 安全，**已实测成立（读写双越权），未修复**】数据级越权（IDOR）：非属主可读他人私有知识库正文，并可删除他人文件
- 实测步骤：admin 建私有库 `qa_r12_priv`(kbId=7, `private_kb=1`) 并上传 `pdf-digital.pdf`；
  用第二用户 `qa_user_b`（role=2，非 admin、非该库创建者）携带自己的合法 token：
  - **读**：`GET /index/knowledgeBase/file/list?kbId=7&type=1` → **200，1 条文件记录**（file id=21）
  - **读正文**：`GET /index/knowledgeBase/file/getFileChunks?kbId=7&docId=21` → **200，2 个 chunk，正文可读**
    （首块以 `Digital PDF sample····2,983,333.33 CNY...` 开头）
  - **写（破坏性）**：`DELETE /index/knowledgeBase/file/delete?id=21` → **200 `success=true` data=true**，
    admin 的文件被非属主删除成功（测试后已由 admin 重新上传恢复，新 id=29）
- 对照（说明过滤只发生在列表层）：`GET /index/knowledgeBase/list` 与 `?kbIds=7` 对 `qa_user_b` 均返回 **0 条**——
  列表有 `create_by` 过滤，但**按 id 直读/直删没有**。
- 代码根因：`KnowledgeBaseListAppServiceImpl:829 getFileChunksByPage` 只校验 kb/doc 存在与解析状态，
  **无 owner / private_kb 判定**；权限体系（`AuthenticateAppServiceImpl`）只有 **URL 级**（path+method）授权，
  没有数据级 ACL。
- 影响：任何具备 index 菜单权限的账号可遍历 `kbId`/`docId` **读取并删除**全平台文档。
- 证据：`evidence/N5-idor-proof.json`、`evidence/D04-idor-variants.json`、
  `evidence/20261024T213354Z-neg4/{results.json,s8_negative_obs.json}` 的 `N5`
- 口径说明：这是**实测后果**，不是"面"。TL 已归入 R13 清单；因可导致跨租户文档泄露与破坏，建议在 R12 交付说明中按"已知高危缺口"单列。

### D-12【严重 / 核心验收点，未修复】答案无引用：引用装配依赖模型在正文输出检索标签，模型不输出即被静默清空
- 现象：S5 两次换措辞提问，均 `200`、模型正常流式输出（357~4134 字），但 `reference` **恒为 `"[]"`**；
  答案文本中没有任何引用标记。
- 三层证据链：
  1. **索引与召回正常**：ES `kb_5 _count=5`；直连 `POST 19995/retrieval_documents`（`score_threshold=0`）
     返回 `documents_list` 非空，元素含 `page_content` 与 `metadata{source,file_path,file_id,search_type}`。
  2. **经 qa-service 同配置 → 引用为空**：`/qa/ai/question_re` 的所有帧 `reference="[]"`，
     `docsTree`/`filePaths` 均为 `null`；模型答句变成"根据现有的参考资料，我们没有找到…"。
  3. **关键实验（决定性）**：用 `score_threshold=0` 的配置再问一次，
     同时读 `rag-qa-service.log` 里 `knowledge---getBody` 的原始响应：
     **`documents_list` 长度 = 4（Java 确实收到了 4 条检索结果）**，
     模型回答也明显在引用上下文（"根据提供的参考资料，这些信息主要涉及客户的授信额度和到期日…"），
     但最终 `reference` 仍为 `[]`。→ **丢失发生在 Java 侧"收到 4 条之后 → 组装引用"这一段**，不是检索没召回。
  4. **代码定位（两层都以"模型必须输出引用标记"为前提）**：
     - Java：`AiServiceImpl:1098` → `filterDocs(content, reference)` → `filterDocuments` 用
       `getIdFromContent(content, "(?<=\\[retrive-tag id=\")[^\\\">]+")` **从答案正文抽标签**再按标签筛选；
       另 `RetrievedData.SimpleDocumentFilter` 只保留 `page_content`/`order_num`，`metadata` 被丢弃，
       引用与文档的对应关系只能靠 `order_num` ↔ 答案标记配对。
     - 前端：`reference_data_transformData` 里同样有
       `referenceMarkId.includes(item.order_num)`（`referenceMark = getA(rawAnswer)`）。
     模型（Qwen2.5-7B-Instruct）本轮**没有输出任何引用标记** → 两侧都把引用过滤成空。
- 结论（事实层）：**检索成功、模型使用了上下文、引用为空**；这是"成果层证据链静默断开"，
  且当前实现把"引用是否出现"完全交给模型自觉输出标记，没有兜底、也没有"无引用降级"标记。
- 为什么定级为严重：这不是"引用为空"的显示问题，而是**检索增强的证据链在成果层被静默切断**——
  用户看到的是无出处的答案，系统不报错、不降级标记，验收点"答案要点必须能在引用原文里找到支撑"无法成立。
- 复测口径：修复方向有二（由实现方选择）：①提示词强约束模型输出 `retrive-tag` 并在缺失时显式标记"无引用降级"；
  ②改为按 retrieval 返回的 doc 直接装配引用（不依赖模型输出标签）。任一方向落地后我按 P1/P2 断言复测。
- 证据：`evidence/20261024T212542Z-full1/s5_answers.json`、`platform/r12/logs/alg_retrieval_service.log`

### D-15【高 / 前端，静态确认 + 实测旁证】引用预览 URL 硬编码内网 MinIO `10.15.12.13:9000`，且对象匿名不可读
- 代码：`frontend/plateform/src/components/CommonEditor/utils/tools.ts:146`
  ```
  file_source: getMarkExcludeType(file_type)
    ? `http://10.15.12.13:9000/${item.metadata.source}`   // ← 内网地址硬编码
    : item.parsedFilePath,
  ```
  该函数（`reference_data_transformData`）正是主链 `SdAiChat/core/useDataTransformer.tsx:60` 把后端
  `reference` 归一化为前端引用对象的入口，因此**每条引用的下载/预览地址都会被拼成内网地址**。
- 实测：
  - `10.15.12.13:9000` 从本环境**不可达**（TCP 连接失败）。
  - 当前 `metadata.source` 形如 `r12-rag/kb_5/pdf-digital.pdf/V0/pdf-digital.pdf`（相对路径），拼出的 URL 在 R12 必然打不开。
  - 即使换成本机正确地址，MinIO **匿名读也是 403**：`http://127.0.0.1:19000/r12-rag/` → 403；
    `http://127.0.0.1:19000/r12-rag/kb_5/pdf-digital.pdf/V0/pdf-digital.pdf` → 403；经 18088 `/minio/` 代理同样 403。
- 结论：**即便 D-12 修好、引用能显示，点击引用仍无法定位/打开正确文件**。应改为后端 `viewFile` 代理或预签名 URL，并去掉硬编码主机。
- 顺带：`frontend/plateform/src/apis/userApi/http-client.ts:46` 另有硬编码兜底
  `baseURL: "http://10.64.13.66:2230/auth"`（另一内网主机），建议一并清理。

### D-16【高 / 后端，实测；已定位为**部署时序**问题】原文预览接口 `viewFile` 500（类加载失败）
- 实测（带 admin token）：
  - `viewFile?fileUrl=r12-rag/kb_5/pdf-digital.pdf/V0/pdf-digital.pdf`（相对路径）
    → 一次 `500 Handler dispatch failed: NoClassDefFoundError: org/apache/tomcat/util/http/Parameters$FailReason`，
    另一次变成 `500 no protocol: r12-rag/...`（说明它用 `new URL(fileUrl)`，**要求绝对 URL**）
  - `viewFile?fileUrl=http://127.0.0.1:19000/...`（绝对路径）→ 仍 `500 NoClassDefFoundError: org/apache/tomcat/util/http/Parameters$FailReason`
  - 同期 `/index/modelInfo/list` 也 500：`NoClassDefFoundError: com/gientech/ragcommon/index/enmu...`，
    而 `/index/knowledgeBase/file/getFileChunks` 仍 200 —— **同一服务内"已加载过的类能用、未加载过的类加载失败"**
- 根因判定（有直接时间戳证据）：`rag-index-service` JVM 启动时间 `05:37:42`，
  而 `rag-index-service-0.0.1-SNAPSHOT.jar` 的 mtime 是 `05:42:44` —— **jar 在 JVM 运行期间被重新构建覆盖**。
  运行中的 JVM 依赖 jar 内的随机访问位置，文件被替换后，之后按需加载的类就会抛 `NoClassDefFoundError`。
  （旁证：`rag-qa-service` 的 jar 未被覆盖，该服务未出现同类错误。）
- **复测结论（重要）**：`rag-index-service` 干净重启（新 pid 213128，启动 `05:44:05`）后，
  `NoClassDefFoundError` **消失**，诊断为部署时序正确。剩下的错误变成：
  `500 Server returned HTTP response code: 403 for URL: http://127.0.0.1:19000/r12-rag/kb_5/pdf-digital.pdf/V0/pdf-digital.pdf`
  → 即 `viewFile` 以**匿名**方式 GET 对象地址，而 MinIO 桶非公开 → 403。
- 因此 `viewFile` 有两条独立约束需要处理：
  ① 只接受**绝对 URL**（相对 `metadata.source` 会 `no protocol`）；
  ② 取对象时必须带凭证或改用**预签名 URL**，否则私有桶恒 403。
- 影响（当前状态下成立）：与 D-15 叠加，构成"引用 → 原文"链路的第二道断点。

### D-13【中 / 配置口径，未修复】默认 `score_threshold=0.1` 与 rerank 实际分数尺度不匹配
- 实测：`bge-reranker-v2-m3` 对本轮查询返回的 relevance_score 为 `1.36e-3 / 2.4e-4 / 3.4e-5 / 2.8e-5` 量级，
  而默认配置 `score_threshold=0.1` → 检索服务日志明确输出
  `查询成功,但是经过重拍模型和FAQ筛选后，查询结果皆小于阈值`，全部召回被丢弃。
- 说明：把阈值设为 `0` 后，检索服务仍返回 1 条，但引用依旧为空 —— 说明**空引用的决定性原因是 D-12**，
  D-13 是叠加的第二层问题（阈值口径不匹配会让召回雪上加霜）。
- 建议：明确"阈值针对的是 rerank 原始 logit 还是归一化概率"，并在默认配置里给出与该模型匹配的量级。
- 证据：`evidence/20261024T212542Z-full1/`、`logs/alg_retrieval_service.log`

### D-14【中 / 功能】PPTX 解析失败（status=4）
- 实测：`image-slide.pptx` 上传 200、fileId=12，最终状态 **4（解析失败）**，无 chunk；
  同批 PDF/DOCX/XLSX/PNG 均 status=3 且有 chunk。
- 影响：指令第七节明确要求 PPTX 可上传并可检索；当前该类型文档不可用。
- 证据：`evidence/20261024T212542Z-full1/results.json`

### D-11【中 / 数据一致性】同一 sessionId 可重复落库，历史恢复可能取到空壳
- 实测（可稳定复现）：先调 `/qa/ai/question_re`（服务端自动建一条 `label=null` 的会话壳），
  再用同一 sessionId 调 `/qa/dialogue/create` → `dialogue` 表出现 **2 条同 sessionId 记录**；
  随后 `getDialogBySessionId` 返回 `label=null` 的那条。
- 代码层：`dialogue` 表对 `session_id` 无唯一约束，写入未做 upsert。
- 反例对照：只调 `dialogue/create`（未先提问）时记录数=1、label 往返一致 → 说明不是普遍现象，而是特定时序。
- 证据：`evidence/20261024T204954Z-s9dup/{results.json,s9_session.json}`

### D-10【中 / 可观测性】检索/编排不可用时，`/qa/ai/question_re` 返回 500 且响应体为空
- 实测（19995/19996 未就绪时）：`http=500`，**body 为空串**，无 `errorCode`、无 `errorMsg`
  （对比：白名单端点会返回结构化错误）。
- 正面事实：**没有**伪造答案（这一点是好的，属 fail-closed），但前端无法区分"服务未就绪"与"问题非法"。

### D-05【中 / 可疑代码，实测未复现】`AuthFilter.filter()` 内两次 `chain.filter()`
- `AuthFilter.java:194-206`：`chain.filter(exchange).then(Mono.defer(() -> { ...; return chain.filter(finalExchange); }))`。
- 实测尝试：同一次 `POST /index/knowledgeBase/create` 只产生 1 条库记录（三个库名各 1 条），
  **不下"必然重复执行"结论**，登记为需维护方确认的可疑代码（写接口尤其需要确认）。

### D-06【低 / 安全】JWT 签名密钥硬编码
- `rag-common/.../JWTUtils.java:22`：`signature = "signature-gien-rag"`。实测缓解有效：
  网关额外要求 `token == redis[user:token:<userName>]`，我用 `qa_user_c` 的 token 改 payload 为 admin 被判 401。

### D-07【中 / 一致性】模型不存在时把错误信息当答案写入对话历史
- `AiServiceImpl:341-345`：`MODEL_NOT_EXIST` 时 `addQuestionAndAnswerRe(..., e.getMessage(), ...)`，
  错误信息被当作一次成功问答持久化。

### D-08【中 / 前端】写作模块 mock 硬编码为 true
- `frontend/plateform/src/components/Template/index.tsx:96` `enableMock: true` → `AiEditor/core/services/servers.ts`
  装 `axios-mock-adapter`，接口回 mock 数据。范围：`pages/HomePage/Writing/EditTemplate`，
  **不在 RAG 主链**（已核 `AIChat/mocks/*` 未进入生产引用链）。

### D-09【低 / 配置】生产 profile 打着 dev 标签
- `frontend/plateform/.env.production` 与 `.env.development` 内容一致（`VITE_ENV= dev`）。

### 不是缺陷（记录以免下轮重复怀疑）
- 登录响应不回显口令/哈希（`userPassword=null`）。
- `/index/knowledgeBase` 未授权 → `401 没有token(30022)`，规范化拒绝成立。
- **413 未复现**：TL 报告的"大文件 413（Spring 默认 1MB）"在我复测时**不成立**——
  `pdf-scanned.pdf`（6,525,683 字节）经 **8088 直连 / 18088 nginx / 15174 vite** 三条入口上传均 `200` 且 `fileSize=6525683` 入库。
  若 TL 是在修复前观察到的，请确认修复是否已生效，避免把已修复项继续列为已知缺陷。

---

## 3. 逐场景结果

> 证据根目录：`platform/r12/qa/evidence/`

### S1 登录与身份 —— PASS（3/3）
菜单 7 项；`userName=admin`；登录响应不含明文/哈希。证据：`20261024T212542Z-full1/`

### S2 建库与检索配置 —— PASS（2/2）
- `POST /index/knowledgeBase/create {"kbName":"qa_r12_indep",...}` → kbId=5，`getKbById` 四项模型字段齐全。
- `POST /qa/search/config/add` → configId=2（独立配置，`knowledge_base_name=kb_5`）。

### S3 上传 5 类文件 —— PASS（5/5）
`pdf-digital.pdf`→9、`docx-table.docx`→10、`table-ledger.xlsx`→11、`image-slide.pptx`→12、`scan-text.png`→13，
全部 `200` 且返回 fileId。证据：`20261024T212542Z-full1/results.json`

### S4 解析完成 + chunk 落地 —— 4 PASS / 1 FAIL
| 文件 | 结果 |
|---|---|
| PDF 数字版 | PASS status=3 chunk=2 |
| DOCX 含表格 | PASS status=3 chunk=1 |
| XLSX 表格 | PASS status=3 chunk=1 |
| 扫描图片 PNG | PASS status=3 chunk=1（OCR 生效） |
| PPTX 图片页 | **FAIL status=4（解析失败，无 chunk）** → D-14 |

### S5 换措辞提问 → 真实模型回答 —— 3 PASS / 2 FAIL
| 用例 | 结果 |
|---|---|
| 提问1（21 字）模型回答 | PASS 200，144 帧，4134 字（首轮，含 mojibake 已定位为我方解码问题并修正） |
| 提问1 返回引用 | **FAIL 引用 0 条** |
| 提问2（24 字，同义改写）模型回答 | PASS 200，324 帧，3358 字 |
| 提问2 返回引用 | **FAIL 引用 0 条** |
| 换措辞命中相同文件（端到端，走引用） | BLOCKED（引用恒空，无法比对） |
| **检索机制：混合召回 + rerank 真实生效**（直连 19995，阈值 0） | **PASS** —— 两种措辞各返回 **4 条且 file_id 完全相同**（9/10/11/13）；`search_type` 分别为 `['es','milvus']` 与 `['milvus']`，证明 ES 关键词 + Milvus 向量混合召回 + rerank 确实在跑（不是纯关键词、也不是 mock）。rerank 分数 1.36e-3/3.46e-5/2.78e-5/2.31e-5 |

> 说明：早期一轮我把 SSE 用 `decode_unicode=True` 读取，跨 chunk 多字节被撕开导致中文 mojibake；
> 已改为按行 bytes→utf-8 解码并复测（`ans_len=400`，文本正常）。这是我方脚本缺陷，不是产品缺陷，特此记录以免误导。

### S6 引用一致性 + 不提交正文 —— 1 PASS / 1 FAIL / 2 BLOCKED
| 用例 | 预期 | 实际 | 结论 |
|---|---|---|---|
| 提问 payload 不含正文 | 字段 ⊆ 白名单且 content≈问题长度 | 6 个字段，`content=21≈问题21` | **PASS** |
| 引用 file_id 归属本库 | 引用指向本库文件 | 无引用可比对 | **BLOCKED**（D-12） |
| 引用要点能在原文 chunk 找到支撑 | 覆盖率 ≥0.6 且页码合法 | 无引用可比对 | **BLOCKED**（D-12） |
| **S6c 点击引用能取到原文** | 200 且拿到字节 | `viewFile` → `500`（类加载，重启后转为私有桶 `403`）；前端 URL 硬编码 `10.15.12.13:9000` 不可达 | **FAIL**（D-15 + D-16） |

- PASS：提问 payload 字段 = `['configId','content','queryId','sessionId','sysType','type']`，
  `content=21 字符≈问题长度 21`，**无任何正文类字段** ——"不随请求提交全文"成立（且是检查实际发出报文，不是靠日志）。
- BLOCKED：引用 `file_id` 归属核对、引用要点→原文 chunk 支撑核对（均因 D-12 无引用）。
  断言已就绪并经变异验证（P1 注入 `999999` → FAIL；P2 注入 `fileContent` 字段 → FAIL）。

### S7 历史对话恢复 —— PASS（3/3）
`getDialogBySessionId` 200 且**包含本轮回答原文头部**（编码修复后复测 `contains=True`，长度 2044）；
`dialogue/list` 200。证据：S7 复测输出见会话 `qa-s7-*`。

### S9 会话完整性 —— 3 PASS / 1 FAIL
创建会话 PASS；label 往返 PASS；单次创建不重复 PASS；
**先提问再建会话 → 同 sessionId 2 条记录、恢复返回 label=None → FAIL（D-11）**。

### S8 负例 —— 7 PASS / 4 FAIL / 1 BLOCKED
| 用例 | 预期 | 实际 | 结论 |
|---|---|---|---|
| N1 无 token | 401/403 + 对照 200 | 401 `没有token`；对照 200 | **PASS** |
| N2 伪造 JWT | 401/403 | alg=none→401、伪签名→401、垃圾串→**500** | **FAIL**（D-03） |
| N3 篡改 payload（qa_user_c→admin） | 401 且不泄露 | 401 `登录失效已过` | **PASS** |
| N4 注销后旧 token | 401/403 | 401 | **PASS** |
| N5 越权读他人私有库 | 403/拒绝 | **200，读到 1 条文件 + 正文 chunk** | **FAIL（严重，D-04）** |
| N5b 按 fileId 直读（不存在 id） | 不返回数据 | 200 `data=null` | **PASS** |
| N5c 越权**删除**他人私有库文件 | 拒绝 | **200 `success=true`，admin 文件被删成功** | **FAIL（严重，D-04 写级）** |
| N5d 越权**枚举**私有库（`kbIds=7` / 无条件列表） | 不得暴露 | 两次均返回 **0 条** | **PASS**（过滤只作用于列表层） |
| N6 白名单未授权可达 | 401/403 | 4 端点全 5xx 进业务层，1 个回显 SQL | **FAIL**（D-02） |
| N7 坏文件（随机字节 .pdf） | 明确失败 | **status=4 失败态，chunk=0** | **PASS**（本轮真实 PASS，不再是环境挡住） |
| N8 扩展名伪装（文本 .pdf） | 明确失败 | **status=4 失败态，chunk=0** | **PASS** |
| N9 删除文档后不得再引用 | 引用不含被删 id | 无法判定（引用恒空） | **BLOCKED** |

证据：`20261024T213354Z-neg4/{results.json,s8_negative_obs.json}`、`N5-idor-proof.json`

> N7/N8 的判定变化值得记录：D-01 未修复时它们"看起来 PASS"（返回 500 7009），但拒绝原因与被测目标无关，
> 我将其降为 BLOCKED；D-01 修复后重跑，才得到"进入 status=4 失败态且 chunk=0"这个**真实的** PASS。

---

## 4. 变异自检（证明断言不是空转）

`python3 qa_suite/mutate.py` → `platform/r12/qa/evidence/mutation-selfcheck.json`

做法：对每条断言，把**真实观察**的关键字段改成"违约值"再喂回同一函数，要求必须翻成 FAIL。

| 用例 | 基线 | 注入违约后 | M1 |
|---|---|---|---|
| N1 无 token | PASS | FAIL | 非空转 |
| N2 伪造 token | FAIL | FAIL | 非空转 |
| N3 篡改 payload | PASS | FAIL | 非空转 |
| N4 注销后复用 | PASS | FAIL | 非空转 |
| N5 越权 | FAIL | FAIL | 非空转 |
| N6 白名单 | FAIL | FAIL | 非空转 |
| N7/N8 坏文件 | PASS | FAIL（status=3,chunk=0 静默成功） | 非空转 |
| N9 删除后引用 | PASS | FAIL | 非空转 |
| P1 引用归属 | PASS | FAIL | 非空转 |
| P2 不提交正文 | PASS | FAIL | 非空转 |
| P3 成功必须有内容 | PASS | FAIL | 非空转 |

**12/12 条断言在注入违约观察后均翻成 FAIL。**

---

## 5. 对开发自检脚本 `acceptance.py` 的断言强度审查

| # | 位置 | 问题 | 后果 |
|---|---|---|---|
| 1 | `s8()`「坏文件上传被明确处理」 | 结论参数**硬编码 True** | 无论返回什么都 PASS，100% 空转 |
| 2 | `s3()` 加密 PDF 负例 | 无"合法文件此刻应成功"的对照 | 环境坏时必然 PASS（本轮已实测复现） |
| 3 | `s6()`「引用携带文件与定位信息」 | 只要求存在 `metadata.source` 字段 | 引用指向别的文件/版本仍 PASS |
| 4 | `s6()`「不随请求传正文」 | 未检查实际发出的 payload | 承诺既未证实也未证伪 |
| 5 | `s5()` | 只判 `len(answer)>10` | **本轮正好命中**：答案 4134 字但引用为空，仍会 PASS |
| 6 | `s4()` | 只判 `status==3` | "状态成功但 chunk=0"的静默成功发现不了 |
| 7 | `s8()` 越权 | 实际测"删除不存在的知识库" | 完全没覆盖本报告 D-04 的真实越权 |
| 8 | `s8()` token 负例 | 只测 1 个 GET、无正向对照 | 端点失效也会被当成"权限生效" |
| 9 | 全局 | 无变异自检 | 无法排除空转 |

> 第 5 条尤其值得注意：若按 `acceptance.py` 判，本轮"引用缺失"这个核心问题**会被判为通过**。

---

## 6. 环境稳定性与复测计划

复核期间网关/index/qa 出现 **4 次**短暂不可用窗口（503 `Service Unavailable` / 连接拒绝，每次 15~40s 后自恢复），
期间用例自动重试。建议交付前确认这是"发布修复导致的计划重启"，而非健康检查抖动。

复测触发条件（任一满足我即重跑）：
1. **D-12 修复**（引用可产出）→ 重跑 S5/S6/S9/N9，解锁"引用归属 / 要点支撑 / 点击定位"三项。
2. **D-14 修复**（PPTX 可解析）→ 重跑 S4 的 PPTX 用例。
3. **D-04 修复**（引入数据级属主校验）→ 重跑 N5，期望结果从 200 变为 403。
4. **D-02 修复**（收敛 `noTokenPaths`）→ 重跑 N6，期望四项全部 401/403。

---

## 7. 边界声明

- 我未修改 `services/**`、`frontend/**`、`platform/r12/conf/**`、`platform/r12/nacos/**`；
  产物仅落在 `platform/r12/qa/**`。
- 夹具：2 个测试用户（`qa_user_b` role=2、`qa_user_c` role=3）、若干测试知识库与检索配置，
  清理 SQL 见 `qa_suite/fixtures.py` 输出，**不自动执行**（执行会销毁证据）。
- 事实 / 推断 / 判断已分别标注：标"实测"的均为本脚本产生；标"代码事实"的为源码可验证但运行时未复现；
  标"推演/判断"的不作为验收结论依据。
- 未经 Owner 授权，本报告不构成任何放行意见；我未以外部独立 QA 身份签署任何内容。
