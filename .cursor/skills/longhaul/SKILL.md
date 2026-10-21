---
name: longhaul
description: LLMKE V1.1.0 longhaul workflow
---

# longhaul

每波读STATE/FAILURES/HANDOFF；仅holder执行已批准argv。达到修复预算停止；状态只由loop_guard更新，Markdown为视图。

唯一合同入口 `contracts/registry.yaml`；当前批次见 `docs/PROJECT-PLAN.yaml`。
