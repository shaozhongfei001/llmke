---
name: contract-check
description: LLMKE V1.1.0 contract-check workflow
---

# contract-check

运行make contract-all，复核跨合同同源、负例、历史数据兼容及lossless生成包；Java/Python实际DTO与校验器需共享样本。

唯一合同入口 `contracts/registry.yaml`；当前批次见 `docs/PROJECT-PLAN.yaml`。
