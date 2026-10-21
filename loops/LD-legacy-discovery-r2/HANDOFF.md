# HANDOFF.md — 批次已 DONE

- 状态：**DONE**（`inventory_gate` dev 自检 pass；`independent_qa_gate` 由 `qa-owner-01` 签名通过）
- 复核命令（注意必须带信任根）：

  ```bash
  cd ~/data/dev/llmke
  export LLMKE_TRUST_ROOT=$HOME/data/qa-keys/trust-root.json
  ~/data/dev/coordination/qa-run.sh memory-check --loop LD-legacy-discovery-r2
  make evidence-check LOOP=LD-legacy-discovery-r2
  ```

- **本批次 DONE 只代表"台账盘点门禁通过 + 证据被独立签署"**，不代表：
  - 任何资产可直接复用（`SOURCE-ASSETS.yaml` 的 `decision` 仍为 null）；
  - 506 条接口等于运行时可路由；
  - P0 有任何关闭（四项仍 OPEN，`make p0-gate` 仍 exit 2）；
  - 业务可交付。
- 后续工作仍按 `loops/LD-legacy-discovery/MATERIALS-REQUEST-V1.0.md` 索取材料；
  任何台账内容的修改都要重跑本批次门禁（会消耗预算）。
