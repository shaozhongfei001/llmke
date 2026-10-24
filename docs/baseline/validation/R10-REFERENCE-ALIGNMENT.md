# 本系统成果与参考源码对齐报告（第十轮，2026-10-24）

> 判定依据全部来自源码实测与命令输出；每条标注 `VERIFIED` / `INFERRED` / `MISSING`。
> 参考源码：`RAG-SRC/_src/gien-rag`（Java）与 `RAG-SRC/_src/rag-alg-service-api`（Python 算法服务）。

## 第一部分 参考系统（基准）

### 1.1 规模（VERIFIED，逐文件统计）

| 执行体 | 文件 | 行数 | 说明 |
|---|---|---|---|
| Java（`gien-rag`） | **1003** | **78,444** | Maven 9 模块，45 个 Controller，**575 个 HTTP 端点**，181 个 `*Service*` |
| Python 算法服务（`rag-alg-service-api`） | **326** | **37,772** | gunicorn 部署，含 Milvus/ES 建表建索引、向量写入、LLM 推理 |
| 合计 | **1329** | **116,216** | — |

### 1.2 Java 模块分布（VERIFIED）

| 模块 | 文件 | 行数 |
|---|---|---|
| `rag-common` | 379 | 17,477 |
| `rag-index-service` | 196 | **25,152** |
| `rag-auth-service` | 187 | 14,577 |
| `rag-qa-service` | 107 | 9,534 |
| `tools` | 71 | 5,412 |
| `rag-graph-service` | 18 | 3,874 |
| `sensitive-words-service` | 24 | 1,374 |
| `elastic-search-service` | 13 | 587 |
| `rag-gateway` | 8 | 457 |

### 1.3 参考系统的能力（VERIFIED：类名/端点/依赖）

| 能力 | 证据 |
|---|---|
| 文档解析 | `FileParseTask*`（DO/Mapper/Repository/Scheduler/Service 全套）、`FileParseUtils`、pdfbox(6 文件)、tika(4)、ocr(14 文件) |
| 切块 | `chunkSize`(32 处)、`chunk_size`(5)、`overlap`(5)，按解析结果切分 |
| 向量化 | Embedding 相关 66 文件；算法服务 `/insert_vector_documents_custom` |
| 向量库 | Milvus 31 文件；`MilvusConfig`、`MilvusMigrateRunnable`；算法服务 `/create_milvus_collection|index|db` |
| 关键词检索 | ES 14 文件 + `elastic-search-service`；算法服务 `/create_es_index`、`/insert_fulltext_documents` |
| 重排 | rerank 21 文件（`RetrieveDoc*Req` 携带重排参数） |
| 生成 | `LlmClient`、LLM 25 文件；算法服务 `/llm_generate_sync`、`/llm_question_rewrite`、`/llm_faq_generate`、`/llm_multi_model` 等 12 个 llm 端点 |
| 图谱 | `rag-graph-service` 18 文件 / 3,874 行；`GraphSearchController`、`GraphDataStatisticsController` |
| 权限 | `rag-auth-service` 187 文件 / 14,577 行；`RoleResourceController`、`PrivilegeController`、`ApiKeyController` |
| 业务对象 | `KnowledgeBaseController`、`KnowledgeBaseFileController`、`FolderController`、`FAQController`、`DialogueController`、`FeedbackController` |
| 管理端接口 | 45 个 Controller / 575 端点，含用户、角色、部门、敏感词、同步日志、系统版本 |

## 第二部分 对齐矩阵

| # | 能力 | 参考系统 | 本系统 | 结论 |
|---|---|---|---|---|
| 1 | 文档解析（PDF/Word/PPT/OCR） | pdfbox+tika+OCR+解析任务调度，196 文件 25k 行 | **无** | MISSING |
| 2 | 切块 | 按 `chunkSize/overlap` 策略切分 | 只有"给定 offset 建块并校验哈希"（`chunk_store` 134 行） | 缺切块器 |
| 3 | Embedding | 66 文件 + 算法服务端点 | **无** | MISSING |
| 4 | 向量检索 | Milvus（31 文件 + 4 个建库端点） | **无**；现为 MySQL `SELECT ... WHERE 谓词` | MISSING |
| 5 | 关键词/全文 | ES 服务 + 索引端点 | **无** | MISSING |
| 6 | 重排 rerank | 21 文件 | **无**（只有字符 bigram 覆盖度打分，`ranking.py` 78 行） | MISSING |
| 7 | LLM 生成 | `LlmClient` + 12 个 llm 端点 | **无**；答案为原文模板拼接 | MISSING |
| 8 | 图谱检索 | 18 文件 / 3,874 行 | **无** | MISSING |
| 9 | 权限体系 | 187 文件 / 14,577 行（用户/角色/资源/API Key） | 113 行：上下文校验 + SQL 谓词 | 仅有过滤，无管理 |
| 10 | 知识库/文档/FAQ/对话/反馈 | 6+ 控制器 | **无** | MISSING |
| 11 | 管理端/控制台 | 45 控制器 / 575 端点 | **2 个端点**（`/answer`、`/healthz`）+ 1 演示页 | 差 3 个数量级 |
| 12 | 敏感词/同步日志/系统版本 | 有 | 无 | MISSING |

## 第三部分 本系统真正完成的东西（事无巨细）

### 3.1 代码规模（VERIFIED，逐文件统计）

| 模块 | 实现文件 | 实现行 | 函数 | 测试文件 | 测试用例 | 测试行 |
|---|---|---|---|---|---|---|
| `answer_api` | 7 | 739 | 20 | 3 | 45 | 669 |
| `citation_evidence` | 3 | 437 | 17 | 2 | 44 | 537 |
| `index_generation` | 2 | 275 | 17 | 3 | 23 | 430 |
| `chunk_store` | 2 | 134 | 5 | 2 | 13 | 220 |
| `authz` | 2 | 113 | 8 | 2 | 14 | 197 |
| `citation_flow` | 2 | 83 | 4 | 2 | 6 | 274 |
| **合计** | **18** | **1,783** | **84** | **14** | **145** | **2,327** |

> 测试代码 2,327 行 > 实现代码 1,783 行。这是事实，也是问题：投入比例倒挂。

### 3.2 数据层

| 项 | 事实 |
|---|---|
| 目标 schema | 43 表 / 538 列，`schema-verify.sh` 可落地（C1–C6 体检 0 不一致） |
| 本系统新增的表 | **5 张**：`document_chunk`、`document_evidence`、`index_generation`、`index_generation_activation`、`index_write_lease`、`index_outbox`（6 张，其中 outbox 属机制） |
| 遗留业务表 | **37 张**（`knowledge_base`、`file_parse_task`、`dialogue`…），本系统**一行代码未使用** |
| 表级差异 | 旧目标 37/478 → v1.3 43/538，差异恰为 6 张机制表 60 列（`p0-02-diff.py` 可复算） |

### 3.3 可运行入口

| 入口 | 能力 | 限制 |
|---|---|---|
| `POST /answer` | 授权上下文 → 取块 → 证据 → 答案 + 引用 + 审计 | 只从 MySQL 按谓词取块；答案为模板拼接；正文需调用方随请求提供 |
| `GET /healthz` | 存活 | — |
| CLI `modules.answer_api.cli` | 同逻辑，无 DB | — |
| 演示页（仓外 `coordination/demo-ui.py`） | 四个场景可视化 | 仅演示 |

### 3.4 逐模块"能/不能"

- **authz（113 行）**：能校验上下文结构与时效、编译 SQL 谓词、图检索降级判定；**不能**管理用户/角色/资源，不做验签。
- **chunk_store（134 行）**：能用给定区间建块并交叉校验哈希；**不能**解析文档、不能决定切块边界。
- **citation_evidence（437 行）**：能构造证据、检测重复 id/区间重叠/解析器版本混用、审计支撑率；**不能**判断内容是否正确。
- **citation_flow（83 行）**：能拼授权取块 SQL、纵深校验越权块；**不能**排序、不能跨库融合。
- **index_generation（275 行）**：能产出代次状态机/CAS 激活/fencing 租约/outbox 的 SQL 与判定；**不执行**，也不调度。
- **answer_api（739 行）**：能 HTTP 应答、错误语义分层、相关性筛选、多版本守卫；**不生成**自然语言。

### 3.5 证据与治理（参考系统没有的部分）

| 项 | 事实 |
|---|---|
| 批次 | 13 个（`DONE 1` / `QA_PENDING 1` / `SUPERSEDED 11`） |
| 摘要 | `control 217` / `code 17` / `doc 17`，`digest_scheme=4`（含命令闭包） |
| 门禁 | `framework-verify` **322 passed / 0 skipped**；`p0-gate` **rc=2** |
| 变异性验证 | 改代码/改控制面/改人工脚本 → 证据失效；还原 → PASS（`verify-kit.sh` 可复跑） |
| 独立 QA | **未签署**（r16 = `QA_PENDING`，`qa-ed25519-indep` 私钥已丢失） |

## 第四部分 完成度结论（诚实口径）

| 口径 | 参考系统 | 本系统 | 完成度 |
|---|---|---|---|
| 实现代码行 | 116,216 | 1,783 | **1.5%** |
| HTTP 端点 | 575 + 30（算法服务） | 2 | **0.3%** |
| 数据表使用 | 37 业务表全用 | 0 | **0%** |
| 产品功能（解析/向量/模型/管理） | 全有 | 全无 | **0%** |
| 证据/治理机制 | 无 | 完整 | **超出参考**（但用户不可见） |

**结论：不是"差一点"，是相差约两个数量级。** 本系统目前是一个可审计的**骨架**：
数据模型、授权谓词、证据校验、代次机制、HTTP 入口都在，但**没有任何一条能让用户上传文档并得到基于语义的回答**。

## 第五部分 达到参考水平所需的技术栈

参考架构（VERIFIED）：`Java 业务服务（9 模块）` + `Python 算法服务（Milvus/ES/LLM/rerank）` + `Milvus` + `ES` + `OCR/解析`。

三条路线：

| 路线 | 做法 | 代价 | 前提 |
|---|---|---|---|
| **A 复刻参考架构** | 引入参考 Java 9 模块，补齐 Python 算法服务 | 最快对齐，但需 JDK/Maven/中间件 | 允许编译 Java、有 Milvus/ES |
| **B Python 重写** | 用现有 6 模块扩成完整服务 | 无 Java 依赖，但要重写 575 端点的业务面 | 允许装包（当前 PyPI 不可达） |
| **C 混合** | Java 网关 + Python 算法（与参考同构） | 折中，参考可直接复用算法服务 | 同 A |

**当前环境硬约束（VERIFIED）**：PyPI 不可达、无 torch/transformers/pymilvus、无 ollama、无 LLM 端点。
因此**现在无法交付"参考水平"的系统**，与投入无关，与依赖有关。

## 第六部分 复现命令

```bash
# 参考源码规模
python3 - <<'PY'
import pathlib
for root in ('<RAG-SRC>/_src/gien-rag','<RAG-SRC>/_src/rag-alg-service-api'):
    fs=[f for f in pathlib.Path(root).rglob('*.java')+pathlib.Path(root).rglob('*.py')]
    print(root, len(fs), sum(sum(1 for _ in f.open(errors='ignore')) for f in fs))
PY

# 本系统
cd ~/data/dev/llmke && make framework-verify > /tmp/fv.log 2>&1; echo "rc=$?"
~/data/dev/coordination/verify-kit.sh --repo ~/data/dev/llmke --loop L0-contract-baseline-r16
```
