# 第四轮并行工作：P0-01 / P0-02 / P0-03 / PDF 验证

- 前提：r5 处于 `QA_PENDING`，等待 `qa-owner` 签署；本节全部工作在**不触碰控制面**的前提下完成
- 产出位置均在被 `source_files()` 排除的目录（`docs/baseline/validation/`、`loops/**`），**未改变 r5 候选指纹**
- 本文件不参与源码快照与冻结控制面

---

## 1. P0-01 接口决策表（506 条，已生成可填 CSV）

产物：`loops/LD-legacy-discovery/evidence/interface-decision-table.csv`（506 行 + 表头）
工具：`loops/LD-legacy-discovery/tools/export_interface_decision_table.py`（可复跑）

### 1.1 静态事实（已核验，勿手改）

| 结论 | 条数 |
|---|---|
| `OK`（路径 + handler 均命中，行号偏差 ≤2） | **504** |
| `LINE_DRIFT`（命中但行号漂移 11 行） | **1** |
| `PATH_ONLY_COMMENTED`（路径仅存在于注释） | **1** |
| 源文件缺失 | **0** |
| 合计 | 506 |

### 1.2 列设计（关键：静态与运行时分开）

| 类别 | 列 | 谁填 |
|---|---|---|
| 已核验事实 | `asset_id`、`stack`、`service`、`method`、`path`、`handler_reported`、`source_file`、`source_line`、`code_evidence`、`code_note` | TL（禁止手改，改了证据就失配） |
| **运行时** | `runtime_route_evidence`（默认 `PENDING`） | `interface-owner` |
| **调用方** | `caller_confirmation`（默认 `PENDING`） | `interface-owner` |
| **在用判断** | `in_use_judgement`（`IN_USE` / `NOT_IN_USE` / `UNKNOWN`） | `interface-owner` |
| 业务 | `business_status`（`KEEP` / `REPLACE` / `RETIRE`） | 业务方 |
| 签署 | `conclusion`（默认 `UNDECIDED`）、`owner_role`、`evidence_link`、`notes` | owner |

> **约束**：`code_evidence ≠ runtime_route_evidence`。
> 「代码里有」不得写成「在用」；`UNKNOWN` 是合法值，禁止为了填满表格而猜。

### 1.3 需要 `interface-owner` 提供的三种格式（任一即可）

| 形式 | 格式要求 | 为什么需要 |
|---|---|---|
| 运行时路由导出 | `service, method, path(原始大小写), handler, framework`，一行一条，附导出时间与环境标识 | 证明「应用真的注册了这条路由」 |
| 网关/接入层日志 | `timestamp, method, path, status, caller_service, count`，至少覆盖一个完整业务周期 | 证明「有人在调」 |
| 调用方书面确认 | 逐条或按 `service + 前缀` 批量确认，注明确认人、日期、覆盖的 `asset_id` 区间 | 日志不可得时的替代证据 |

**P0-01 关闭仍需**：三方差异归零（清单 / 源码 / 运行时）+ 约 380 条在用判断 + `/retrieval_qa` 书面决议。
本 CSV **不构成**关闭证据。

---

## 2. P0-02 字段级对照（在既有 37 表对照上补全）

### 2.1 先说一个硬缺口

`docs/reuse/DATABASE-ASSETS.yaml` 的 37 个条目**只有 `model_field_count`，没有字段名清单**（无 `fields` 键）。
因此「台账字段名 ↔ DO 字段名」目前只能做**单向**：实体侧有名字，台账侧只有计数。

→ 已记为需 `data-owner` 补的输入：**字段级清单或真实 DDL**。在补齐前，任何字段级 diff 都只能是
「实体有 N 个字段、台账记 M 个」，不能断言「台账漏记了哪一列」。

### 2.2 四张计数不符的表（实体侧逐字段）

| 表 | 台账 | 实体 | 差 | 实体字段 |
|---|---|---|---|---|
| `re_embedding_file` | 13 | **14** | +1 | id, taskId, kbId, kbName, fileId, gmtCreate, gmtModified, totalChunkNum, processedChunkNum, errorChunkNum, isDel, isMigrate, status, lastError |
| `re_embedding_retry_task` | 12 | **13** | +1 | id, uid, taskId, type, payload, lastError, gmtCreate, gmtModified, retryTimes, isDel, status, fileId, kbId |
| `re_embedding_task` | 13 | **14** | +1 | id, kbId, kbName, embeddingModelName, status, isDel, logSummary, gmtCreate, gmtModified, msgKey, totalFileNum, uid, createBy, modifiedBy |
| `user_operate` | 13 | **12** | −1 | id, gmtCreated, gmtModified, name, url, startTime, endTime, userId, userName, params, ip, success |

> 三张 `re_embedding_*` 一致地多 1、`user_operate` 少 1。**没有 DDL 无法判定谁对**：
> 可能是台账按 DDL 记而实体多了非持久化字段，也可能实体继承/漏映射。
> **禁止为了「凑数」去改实体或台账**——已在报告中明确禁止该做法。

### 2.3 `dialogue` 的事实（重点）

| 字段 | 类型 | 列名 | 结论 |
|---|---|---|---|
| `createBy` | String | `createBy` | **存在** |
| `userId` / `user_id` | — | — | **不存在** |
| `kbId` | Long | `kbId` | 存在 |
| `config` / `configHistory` | String | 同名 | **疑似 JSON 列**（未验证） |

源码路径：`gien-rag/gien-rag/rag-parent/rag-qa-service/src/main/java/com/gientech/ragqaservice/domain/model/DialogueDO.java`

**关键洞察**：`dialogue` 实体 13 字段 = 台账 13 字段，**计数一致**，但语义不等价——
设计文档要求给 `dialogue` 建 `user_id` 索引，而实体里根本没有这一列。
→ **计数一致 ≠ 语义对齐**，这是 P0-02 必须用真实 DDL 才能裁定的原因。

### 2.4 未知项（必须由 DDL 回答，不得推断）

| 未知项 | 为什么静态看不出来 |
|---|---|
| 继承字段 | 实体未 `extends` 基类时看不到父类列 |
| 逻辑删除 | `isDel` 是否参与唯一索引/查询条件，取决于 DDL 与 SQL |
| JSON 列 | `config`、`configHistory`、`payload`、`params` 可能是 JSON/TEXT，长度与索引不同 |
| 索引/约束/触发器 | 实体类完全不表达 |
| 引擎/字符集/排序规则 | 同上 |
| 列名映射 | 无 `@TableField` 时按驼峰猜下划线，`createBy → create_by` 需 DDL 证实 |

### 2.5 结论口径

全部标 **`CANDIDATE`**。**不关闭 P0-02，不修改数据库设计去迎合静态字段数。**

---

## 3. P0-03 安全证据草案（E1–E8 + 六类负例）

> 状态：**草案 / 待 security-owner 批准**。未在任何真实检索链上执行，**不得**作为生产安全证据。
> 禁止把测试夹具、模拟服务、设计说明当成生产证据。

### 3.1 E1–E8 证据清单

| 编号 | 证据 | 交付形式 | 现状 |
|---|---|---|---|
| E1 | 授权上下文规范（`AuthContext`：服务、KB/文件范围、授权版本、有效期、请求标识） | 字段定义 + 签名规则 + 失效语义 | **草案待批** |
| E2 | 越权读：请求 KB 外文件 | 可执行负例 + 期望 `DENY` + 日志 | 未执行 |
| E3 | 目录聚合越权：目录授权但子文件被 deny | 负例（验 deny 优先） | 未执行 |
| E4 | 撤权即时性：撤权后同一 token 立即失效 | 负例（验缓存带版本） | 未执行 |
| E5 | FAQ 继承：FAQ 命中但来源文档无权限 | 负例（验按来源复核） | 未执行 |
| E6 | 图路降级：仅部分文件授权时不得走整 KB 图路 | 负例（验 `degraded` + 覆盖度） | 未执行 |
| E7 | 邻近块/图片回查的二次取数 | 负例（验二次取数仍带范围） | 未执行 |
| E8 | 检查对象声明（哪些接口/路径纳入检查） | 清单 + 覆盖度声明 | **草案待批** |

### 3.2 六类负例断言（草案）

1. **跨 KB**：`kb_id ∉ 授权集` → 拒绝，且响应不含任何内容片段（不是「空结果」）；
2. **跨文件**：同 KB 内 `file_id ∉ 授权集` → 拒绝，**邻近块扩展不得绕过**；
3. **deny 优先**：任一路径来源为 deny → 整体拒绝（即使其他来源 allow）；
4. **撤权即时**：撤权后 ≤1 请求内失效（缓存必须带授权版本号）；
5. **FAQ 继承**：FAQ 命中 → 回查来源文档权限；无权限则拒绝（不允许「FAQ 不受授权影响」）；
6. **图路隔离**：非整 KB 授权 → 图路不参与，响应标 `degraded` 并给出覆盖度。

**通过判据**：六条全部 `DENY`/`degraded`，且不泄露内容；任一条返回内容即失败。

---

## 4. PDF 集成验证（doc2md 路线）

### 4.1 就绪度实测（已落盘）

证据：`loops/LD-legacy-discovery/evidence/pdf-verification-readiness.json`

| 臂 | 状态 | 原因 |
|---|---|---|
| 旧解析臂（`alg_doc_parse_service`） | **NOT_RUNNABLE** | 缺 `magic_pdf`、`onnxruntime`、`cv2`、`tika`、`fitz`（仅 `pdfminer`、`docx` 可用） |
| doc2md 臂 | **NOT_RUNNABLE** | 无 `.venv`，包不可导入（`ModuleNotFoundError: doc2md`） |

样本（6 份，已记录 SHA256 与字节数）：`pdf-digital.pdf`、`pdf-scanned.pdf`（6.5 MB）、`pdf-encrypted.pdf`、
`docx-plain.docx`、`docx-table.docx`、`docx-image.docx`。doc2md HEAD `d9e4f983`，工作树干净。

### 4.2 验证协议（一旦两臂可运行即可执行）

| 要素 | 要求 |
|---|---|
| 两臂记录 | 各自**实际加载的解析器文件绝对路径**、文件 SHA256、`git rev-parse HEAD` |
| 防伪列 | 报告中必须输出两臂的解析器路径并在断言中断言不同（防止上一轮的「自己和自己比」假绿） |
| 非空断言 | 输出字符数 > 0、块数 > 0、每块 `page_number`/`offset` 合法；任一侧 `ok=False` 即判 `FAILED`（不得 `None == None` 判等） |
| 覆盖矩阵 | 文本 PDF / 扫描件 / 加密 PDF / 表格 DOCX / 图片 DOCX / 空文件 / 损坏文件 |
| 比较维度 | 文本内容（归一化空白）、块数、页号、offset、元数据、引用定位、错误处理 |
| 既有 61 项测试 | 仅作**组件回归**证据，**不作为** LLMKE 集成等价证明 |

### 4.3 为什么不能用 pdfplumber 兜底

`pdfplumber` 与旧系统在版面还原、表格切分、OCR 路径上不等价。静默切换会得到
「测试通过但能力缺失」的结果，属于掩盖缺口。若最终必须用它，需写成**显式缺口**并由业主决策。

### 4.4 需要的外部输入

| 输入 | 责任方 | 用途 |
|---|---|---|
| 旧解析臂依赖（`magic_pdf` 离线包 + 版面/OCR 模型目录） | `algorithm-owner` | 让对照臂可运行 |
| 或：旧系统对 6 份样本的**参考输出**（含块级偏移） | `algorithm-owner` | 无环境时以参考输出作对照 |
| doc2md 运行环境（venv / 依赖清单） | doc2md 维护方 | 让新臂可运行 |
| 真实业务 PDF 样本（≥3 类版式，脱敏） | 业务方 | 代表性覆盖 |

**本轮结论：PDF 等价性未验证**（两臂都跑不起来）。不写「已覆盖」，也不写「已知通过」。
