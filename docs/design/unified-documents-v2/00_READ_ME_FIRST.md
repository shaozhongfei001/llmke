# LLMKE设计与契约重核包 V2.0

日期：2026-10-30。用途：先核对设计和机器合同，再确定实施拆分；**不是长程开发提示词，不是实现/投产证明**。

## 已确定的设计方向

1. 上传文件统一经实际doc2md，保留其冻结三件套、Document IR 1.0与资产。
2. RAG与图引擎共同消费版本化产物与语义伴随文件；Graph直接读MD/IR，不依赖ES或RAG切片。
3. 长文仍按真实上下文预算做结构化抽取窗口，保留原文覆盖和来源。
4. 目标部署不强制ES；关键词/精确/混合检索须由通过验证的后端承接。
5. HippoRAG是首个适配目标；标准文档包、GraphEnginePort、来源身份和业务回答独立于框架。
6. 社区与结构化报告独立实现/验收，不因选HippoRAG而删除，也不冒称其原生已有。

## 阅读顺序

| 文件 | 解决的问题 |
|---|---|
| 01_UNIFIED_DESIGN_V2.md | 上传→解析→共享输入→RAG/Graph→证据与发布的整体逻辑 |
| 06_STANDARD_INPUT_AND_GRAPH_ENGINE.md | MD、表格、图片理解结构，以及HippoRAG可替换边界 |
| 05_ES_AND_GRAPH_INPUT_DECISION.md | 用户建议的合理部分、需限制部分及去ES判据 |
| 02_RECONCILIATION_AND_DECISIONS.md | 原设计/原合同/源码事实与本次裁定的区别 |
| 03_CONTRACT_CHANGE_MATRIX.md | 机器合同、所有者、版本与迁移边界 |
| VALIDATION_REPORT.md / OFFLINE_CHECK.json / UPSTREAM_IR_CHECK.json | 本轮实际验证及不能推出的结论 |
| SOURCE_INVENTORY.json | 原包摘要、核对过的材料、代码基线和外部来源 |

机器合同在contracts/；正反例在tests/test_document_pipeline_v2_contracts.py；合成样例在examples/，多模态样例在examples/multimodal/。

## 复算

应用补丁至本包记录的基线或完成显式冲突审查后，在独立工具环境安装本目录validation-requirements.lock；这是合同检查环境，不是产品运行依赖：

```bash
python scripts/document_pipeline_v2_offline_check.py
python scripts/document_pipeline_v2_validate.py
python -m pytest tests/test_contract_semantics.py tests/test_document_pipeline_v2_contracts.py -q
```

第一个命令先把OpenAPI引用解析成内存本地包，再禁用网络验证。它没有调用或伪装成通用contract_generate/check的成功记录；原因和边界见验证报告。原doc2md纯IR校验报告绑定提供源码文件SHA256，完整doc2md运行仍需原项目环境。

## 当前状态

- 本包已有设计、schema/API/事件/来源/规则/验收合同、可核对的合成样例和一致性检查。
- 未实现新HTTP端点、HippoRAG适配器、doc2md全格式接线、去ES迁移、真实图谱构建或目标机发布。
- 不自动关闭任何原P0、不签署独立QA、不修改外部main/生产环境。
- 原架构相关R15L任务书仅作历史记录；没有给CodeBuddy派发本包实施任务，也没有声称已停止外部正在运行的进程。
