# V2.0 设计与契约接入报告

日期：2026-10-30　角色：Tech Lead（TL）　状态：**设计/契约已接入，业务实现未启动**
分支：`design/v2-input-engine-adoption-20261030-2101`　起点：`419a87d`

> 本报告只说明"设计包是否已正确进入仓库、契约是否可被工具解析与生成"。
> 它**不**表示 doc2md/HippoRAG/社区/去 ES 已实现，也**不**构成独立 QA、业务验收或投产申请。

---

## 1. 输入核验

| 项 | 结果 |
|---|---|
| ZIP SHA256 | `a56f598b92c27cb9216591c8dc74c7f5221b7f1cd9fb2f456bc42456877465de` — 与给定值一致 |
| 成员数 / 路径安全 | 64 项；无绝对路径、无 `..` 穿越、无符号链接 |
| 解压位置 | 仓外独立临时目录；**未**解压覆盖仓库根，包内 README/contracts 未盲目替换 |
| `MANIFEST.sha256` | 63 项逐一校验通过（清单不含自身），与包内说明一致 |
| 补丁 SHA256 | `8d5d062ed4e41353b9368cb45f17f759f7fc079a8d0eee0b3aca69859d954cb8` — 与给定值一致 |
| `PACKAGE_STATUS.json` | base `3fea44e`、59 changed files、`business_implementation_files_changed: 0`、未推远端、未发布 |

仓库事实（决定起点）：

- `main` 工作树 HEAD `a144020`，**不含**补丁基线，且有 405 项历史未提交改动 → 不在其上开刀。
- R12 工作树 HEAD `419a87d`，`3fea44e` 是它的直接祖先（两者之间只多一个 `docs/r15/HANDOFF-20261030.md` 提交）。
- 因此按"当前 HEAD 晚于补丁基线时以当前 HEAD 为起点"，从 `419a87d` 建独立工作树与分支，未回退到旧基线。
- `git apply --check` 全 59 文件通过；`git apply --index` 应用成功，无 `.rej`、无重复应用。

> 包内"95 项测试 / 27 份合同通过"是提供方自查记录，本报告 §4 给出的是**本仓库本环境的实测**，两者分开记账。

---

## 2. 设计吸收结论

### 2.1 采纳（已进入设计与合同）

1. 解析入口统一为 doc2md；平台只封装其冻结三件套 + Document IR 1.0 + 资产，不另造竞争正文模型。
2. `parsed_text.md` 是**不可变证据坐标基准**（UTF-8 码点、左闭右开），不再表述为"展示文件"。
3. 平台自有对象：ParseArtifact / InputSnapshot / KnowledgeInputBundle / DocumentSemantics；RAG 与图绑定同一解析与语义版本。
4. 图构建直读 MD/IR，不以 RAG chunk、ES、预向量化为前置；长文用结构化抽取窗口 + 预算 + 覆盖检查，禁止静默截断。
5. HippoRAG 为首个适配目标，隔离在 GraphEnginePort 之后；公共身份/业务接口不绑 native ID、类或私有序列化。
6. 社区 / 结构化报告 / global 是**必选独立能力**，不因选 HippoRAG 而删除，也不冒称其原生已有。
7. ES 从"必选默认"降为"迁移期可选适配器"，中文关键词/精确标识/混合检索能力必须由验证过的后端承接后才可停用。
8. 权限域与代次先于构建：构建前隔离可见集合、撤权先设读取围栏、同一次查询固定发布版本、普通 RAG 可独立就绪。

### 2.2 修正与差异（有源码依据，非照单全收）

| # | 包内表述 | 当前源码事实 | 处置 |
|---|---|---|---|
| M-1 | 社区能力"必选"，输入为完整有效顶点集、合法孤点保留 | `graph_community.py:38-40` 只 `MATCH (a:entity)-[e:relationship]->(b:entity)`，66 个孤立顶点不进社区视野 | 记入队列 VL4-01；设计正确，代码待改 |
| M-2 | 社区"优先原设计 Leiden" | 现网 `graph_community.py:64` 用 Louvain；设计未给等价范围 | 记入 VL4-01 裁定项：先给 Louvain/Louvain 层级与 Leiden 的差异说明再决定是否替换，不静默换算法 |
| M-3 | 抽取窗口"不得静默截断尾部" | `graph_service.py:552-558` 按 `max_char_length=15000` 硬截断，无日志、无标记、无覆盖校验 | 记入 VL2-06（GraphExtractionPlan 最小版） |
| M-4 | SourceRefV2 以 artifact + MD offset 为原文身份 | local 检索 `retrieval_fun_tool.py:759` 的 `order_num` 是**检索期随机 UUID**，真实 chunk 主键在 `:762` 的 `pk`；Java 侧按 `order_num` 过滤引用（`AiServiceImpl.java:1905-1926`） | 记入 VL1-04：引用必须可反查到原件与 offset |
| M-5 | 包内说 R15/R15L 任务书"仅作历史记录" | `docs/r15/TASKS.yaml` 的 20 项仍是 `docs/PROJECT-PLAN.yaml` 中 L1/L2 loop 的在册任务 | **不采纳"作废"**：改为统一队列里的映射关系（见 IMPLEMENTATION-QUEUE-V2.md §2），不重置未完成任务 |
| M-6 | 图解析"未实现/无调用" | 现网已有调用与零产出闸门（`FileAppServiceImpl.java:611-623`、`:630-644`） | 保留现状，不重复建设 |

### 2.3 发现的合同内部矛盾（已出 CR 定稿，2026-10-30 补记）

- 原 `contracts/ontology/relations.v1.json` 的 `consumer_contract.reverse_dedup` 写："symmetric=false 的谓词反向是不同事实，**不得互相覆盖**"。
- 但外部评审 B01 的修法要求"按本体 symmetric/inverse/**domain/range** 分流"，即端点类型不满足 domain/range 时反向是**伪反向边**应被拒绝。二者对"非对称谓词的反向"给出不同结论。
- **处置（已执行）**：登记 CR `BL-2.0.0-01`（`docs/policies/CHANGE-REQUESTS.yaml`，status ADOPTED，owner tech-lead），并把合同改为按对称性分流 + 新增机器可读 `direction_resolution` 块（含 `forbidden: [sorted_undirected_key_for_all_predicates, first_writer_wins]`）。
- 兼容边界：谓词清单、symmetric 取值、类型码与 payload 语义均未变；只补齐"非对称谓词反向如何处置"，并显式禁止旧的"一律无序键 + 先到者"。存量边不迁移。
- 验收实测（对 R12 工作树的 B01 候选实现逐条跑，2026-10-30）：

  | CR 验收项 | 结果 |
  |---|---|
  | 甲担保乙 与 乙担保甲 两条都在（未登记谓词 → 方向不可裁决） | PASS（2 条，`direction_unresolved_count=1`） |
  | `A-利率基准->B` 反向被拒（端点类型违反 product→metric） | PASS（保留 1 条，`spurious_direction_count=1`） |
  | 相似/关联 双写只留一条 | PASS（`symmetric_dedup=1`） |
  | 合同 `direction_resolution.forbidden` 含两项禁止规则 | PASS |

  改动后复跑：`make contract-all` PASS、`make contract-v2-check` PASS（95 passed）、`generated/` 未受影响（本体不参与生成）。

### 2.4 未决（材料不足，不能宣称）

doc2md 最新源码/制品与全格式出口、HippoRAG 锁定版本与离线依赖、真实 DDL 与恢复副本、目标机容量/质量阈值、真实 ES 职责基线。

---

## 3. 本次实际改动

### 3.1 来自补丁（59 文件，`business_implementation_files_changed: 0`）

合同 11 个（schema/api×2/events/evidence/rules/evaluation/registry/ontology×2/README）、设计文档 8 份、合成样例与检查清单 37 个、检查脚本 2 个、测试 1 个。逐项见 `git diff --cached --stat`。

### 3.2 接入所需的最小技术适配（TL 自决，逐条给原因）

| 文件 | 改动 | 原因 |
|---|---|---|
| `scripts/contract_runtime.py` | 新增 `bundle_local_refs()` 与 `no_network()` | 合同使用仓内 `$id` 的绝对引用；通用校验器会真去抓 `https://llmke.local/...` |
| `scripts/contract_toolchain.py` | API 校验改为先内存打包本地 ref 再校验；语义校验全程禁网，出网即判失败 | 同上；保证"碰巧没网"不能冒充通过 |
| `Makefile` | 新增 `contract-v2-check` 目标 | 让 V2 自查可被一条命令复算，不靠口口相传 |
| `docs/baseline/TRACE.yaml` | 增登 9 条 V2 合同（decision_id = `DOC2MD-UNIFIED-2.0.0`，取 registry 的 `design_revision.id`） | registry 与 TRACE 合同集必须严格相等，否则 trace-check 恒红 |
| `contracts/README.md` | 更新"generated 尚待生成"为实际状态 | 该句在生成完成后已过时 |

**证据（为什么必须改，不是风格问题）**：改造前执行 `make generate` 的真实报错为
`Unresolvable: https://llmke.local/contracts/schema/llmke-core.json#/$defs/TokenBudget/properties/policy_id`，
且抓包栈显示 `HTTPSConnection(host='llmke.local', port=443)` —— 即校验器**确实发起了出网尝试**，与包内 `VALIDATION_REPORT.md:24` 记录的审批拒绝理由一致。改造后同命令不再有任何网络动作，未知外部引用直接失败。

### 3.3 明确**没有**做的事

未改旧 v1 schema/API 字节；未新建第二套合同 ID；未改 registry 的 `baseline_version`；未重新冻结 `FROZEN-MANIFEST.json`；未改 `contracts/ontology/*` 的 payload；未动业务源码；未停任何服务；未建索引；未合并 main；未推远端。

---

## 4. 实测结果

工具环境：仓外独立 venv，Python 3.10.12，按 `validation-requirements.lock` 安装；
实测 `jsonschema 4.23.0 / openapi-spec-validator 0.7.2 / referencing 0.36.2 / PyYAML 6.0.2 / pytest 8.3.5` 与锁一致；
唯一偏差 `lazy-object-proxy 1.12.0`（锁要求 1.13.0，本机索引无该版本，属传递依赖）。
该环境不写回仓库依赖锁，也不影响共享算法环境。

| 命令 | 退出码 | 结果 |
|---|---|---|
| `python scripts/document_pipeline_v2_offline_check.py` | 0 | `PASS`，`contract_count=27`，`network_attempts=0` |
| `python scripts/document_pipeline_v2_validate.py` | 0 | `PASS`（合成样例一致性；`product_e2e=NOT_EXECUTED`） |
| `pytest tests/test_contract_semantics.py tests/test_document_pipeline_v2_contracts.py -q` | 0 | **95 passed** |
| `make generate` | 0 | `PASS (27 contracts, clean staged outputs)` |
| `make check` | 0 | `PASS (27 contracts, semantic + exact linkage)`；`generated/` 17 个产物与 registry 声明精确相等 |

`generated/` 变化核对：3 个既有 `sdk/*.types.json` **纯增行**（各 +3738 行，`schema_resources` 11→12，即新增 V2 schema 被内嵌），无删改；新增 3 个 V2 产物（`schema/llmke-document-pipeline-v2.snapshot.json`、`sdk/llmke-document-pipeline-api-v2.types.json`、`sdk/llmke-graph-engine-api-v1.types.json`）。

其余门禁（如实记录，**不**冒充通过）：

| 检查 | 打补丁前（`419a87d`） | 本次分支 | 结论 |
|---|---|---|---|
| `trace-check` | FAIL：2 份本体未登记 + loop 集漂移 | FAIL：仅剩 loop 集漂移（`loops/R12-real-rag` 未登记进 PROJECT-PLAN） | 合同集已对齐；loop 漂移为既有，属治理登记，未擅自补 |
| `security-check` | 命中 1861 条（R12 平台配置含真实连接串/口令/个人路径） | 命中 1861 条，**新增 0** | 既有问题，未由本次引入 |
| `baseline-check` | FAIL：`.gitignore` 冻结漂移 | FAIL：追加 `contracts/registry.yaml`、`contracts/README.md` 漂移 + 新合同文件 | 重新冻结属技术基线变更，需独立评审，TL 不单方执行 |
| `pytest tests/` | — | 228 passed / 3 skipped / 1 failed（`test_security_scan.py::test_framework_repo_itself_is_clean`，即上表既有命中） | 无本次引入的失败 |

---

## 5. 兼容边界（这些结果不能推出什么）

- 合同与样例通过只证明**形状/引用/清单/摘要/就绪条件**自洽，不证明模型执行、token 计数真实、金融命题被原文支持。
- 27 份合同登记、`generated` 同步 **不**等于已实现；V2 合同 `x-lifecycle` 仍为 `DESIGN_REVISED_NOT_IMPLEMENTED`。
- 旧 v1 18 份合同的冻结/业务证据状态未变；本次新增登记不构成业务批准。
- `DV-01…26` 全为 `NOT_EXECUTED`，不能被 95 条测试顶替。
- 未获独立 QA 签署、未获生产批准、未做目标机安装。

---

## 6. 未决项

| 编号 | 未决内容 | 影响 | 下一动作 |
|---|---|---|---|
| ~~U-01~~ | ~~relations.v1.json `reverse_dedup` 与 B01 domain/range 判定的矛盾~~ | **已关闭 2026-10-30**：CR `BL-2.0.0-01` 定稿（status ADOPTED），合同改为按对称性分流并新增 `direction_resolution`；四项验收判据对候选实现实测全 PASS | 随 VL2-01 合入 B01 实现 |
| U-02 | doc2md 源码/制品未入库、未验证当前版本与全格式出口 | VL1 切片的前置 | **部分解除（2026-10-30）**：doc2md 源码在本机工作区可读，HEAD `d9e4f98`，交接基线 `52a63ec` 为其祖先，统一批量入口 `backend/app/extensions/intake/batch.py`。仍缺：制品与依赖 hash 登记、四类格式真实运行、与包内 `doc2md.zip SHA 63eede32…` 的对应关系 |
| U-03 | HippoRAG 锁定 commit/依赖/模型 | VL3 无法开工 | 选定版本 + 离线 wheel + 模型端点，登记制品 hash |
| U-04 | `loops/R12-real-rag` 未登记进 `docs/PROJECT-PLAN.yaml` | trace-check 恒红 | 由流程所有者决定是否登记 R12 loop；TL 不代改计划 |
| U-05 | `FROZEN-MANIFEST.json` 未含 V2 合同 | baseline-check 恒红 | 待 V2 合同通过评审后按冻结流程重冻结（需授权人字段） |
| U-06 | `lazy-object-proxy==1.13.0` 在可用索引不可得 | 工具环境与锁有 1 项偏差 | 补 1.13.0 wheel 或由提供方把锁降到可用版本 |
| U-07 | 真实 DDL / 恢复副本缺失（`platform/r12/db/gienrag.sql`、`nacos/configs.json` 均不在仓库） | VL5 代次与迁移无法验证 | 从授权环境导出并登记，禁止编造 |
| U-08 | **doc2md 当前不产出 Document IR**：`parse-markitdown` 只写三件套（`backend/app/services/markitdown_parser.py:437-483`），`parse-mineru-pdf` 额外写 `ir_source/`（`mineru_pdf_parser.py:624`），两条路径都未调用 `services/document_ir_builder.py`；`parsed_metadata.json` 也不含 `content_uid`（只有 `parse_manifest.json` 有） | V2 `ParseArtifact` 要求 `document_ir` + `metadata.content_uid`；当前真实出口**无法**满足 | **部分处置（2026-10-30）**：已出 CR `BL-2.0.0-02` 增加并列对象 `LegacyTextArtifact`（三件套、state 固定 PARTIAL、能力枚举只允许 text/source_alignment），text-only 产物有了合法登记位且不能冒充结构化；**真正走 ParseArtifact 仍需 doc2md 补 IR 出口**（改其仓库，需维护方） |
| U-09 | doc2md 真实解析的运行依赖缺口：本机唯一可用解释器（conda base）缺 `markitdown` 包；共享算法环境不允许安装 | 无法在本机产出真实四件套 | 由业主指定可安装的独立 venv，或提供已解析的真实产物样本 |
