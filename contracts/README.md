# 受控合同 V1.1.0

18份合同见registry。11份JSON Schema共享core并保留完整约束，3API只引用共享schema；其余为semantic/evidence/evaluation/error规则。make generate空目录生成；make check验证语义、跨合同一致性和精确产物联动。generated为验证包，不是已编译DTO SDK。业务状态机另运行contract_runtime与业务回放；政策文件不代表真实批准。

## 2026-10-30设计修订（尚未实施）

原18份合同仍为旧兼容面；新增统一文档V2的6份合同、引擎port的1份API，以及2份原有本体lookup登记，当前共27项。旧v1 schema/API未改。新增对象不代表运行代码已接线，也没有改变旧冻结/批准状态。

设计入口：`docs/design/unified-documents-v2/00_READ_ME_FIRST.md`；标准MD/表格/图片输入和HippoRAG隔离见`06_STANDARD_INPUT_AND_GRAPH_ENGINE.md`。

本次使用显式禁止网络的`document_pipeline_v2_offline_check.py`检查本地registry/schema/ref/OpenAPI；不把它当原generate/check的通过证据。新合同登记的generated输出尚待在安全本地解析配置下重新生成，原generated不能当V2已同步。详见该目录VALIDATION_REPORT.md。
