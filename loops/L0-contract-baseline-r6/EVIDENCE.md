# L0-contract-baseline-r6 证据

本批次是 W-01 收口候选。与 r5 同组 8 条门禁，不放大 pass 条件。
证据文件在 `evidence/`，由 `run_batch` 逐条写入；本文件只做索引，不复制日志内容。

- 新增绑定：`code_digest`（modules/apps/services/lib/frontend 的实现代码）
- 受其约束的门禁：`independent_qa_gate`（argv 为 `make framework-verify`，含模块测试）
- r5 的证据与日志原样保留，**不得**作为本批次验收依据
