# 受控合同 V1.1.0

18份合同见registry。11份JSON Schema共享core并保留完整约束，3API只引用共享schema；其余为semantic/evidence/evaluation/error规则。make generate空目录生成；make check验证语义、跨合同一致性和精确产物联动。generated为验证包，不是已编译DTO SDK。业务状态机另运行contract_runtime与业务回放；政策文件不代表真实批准。

## 2026-10-30设计修订（尚未实施）

原18份合同仍为旧兼容面；新增统一文档V2的6份合同、引擎port的1份API，以及2份原有本体lookup登记，当前共27项。旧v1 schema/API未改。新增对象不代表运行代码已接线，也没有改变旧冻结/批准状态。

设计入口：`docs/design/unified-documents-v2/00_READ_ME_FIRST.md`；标准MD/表格/图片输入和HippoRAG隔离见`06_STANDARD_INPUT_AND_GRAPH_ENGINE.md`。

2026-10-30 接入更新（`docs/design/unified-documents-v2/ADOPTION_REPORT_20261030.md`）：原通用 generate 在 V2 合同上实测会尝试抓 `https://llmke.local/...`（DNS 失败并报 `Unresolvable`），与包内记录的审批拒绝理由一致。现已在 `scripts/contract_runtime.py` 增加仓内 `$ref` 内存打包与校验期禁网（未知外部引用直接失败），`make generate` / `make check` 已在 27 份合同上实测 PASS，registry 声明的 17 个 generated 产物与 `generated/` 精确相等。`document_pipeline_v2_offline_check.py` 与 `document_pipeline_v2_validate.py` 仍保留为独立的样例/引用自查（`make contract-v2-check`）。合同通过不代表已实现，详见该目录 VALIDATION_REPORT.md 与接入报告。

## 2026-11-05 登记更新（HybridRetrieval 1.0）

新增 1 份规则契约 `llmke-hybrid-retrieval-invariants-v1`（`rules/llmke-hybrid-retrieval.yaml`，HR-01~HR-10），锁定「统一向量库 + 统一来源身份（平台 pk）+ dense/lexical/graph 三路按 pk 融合」的架构约束。它是 DP 系列的检索侧补充，不改变旧 v1 契约与冻结状态。设计入口：`docs/design/unified-documents-v2/11_VECTOR_STORE_AND_HYBRID_RETRIEVAL.md`。当前登记共 28 项。
