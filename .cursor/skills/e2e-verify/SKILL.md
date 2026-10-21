---
name: e2e-verify
description: LLMKE V1.1.0 e2e-verify workflow
---

# e2e-verify

按CASE-REGISTRY运行真实数据正负例，不用页面可见代替权限/状态机验收；检查LLM上下文、业务结果与引用。产物缺失保持BLOCKED。

唯一合同入口 `contracts/registry.yaml`；当前批次见 `docs/PROJECT-PLAN.yaml`。
