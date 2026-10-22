# L0-contract-baseline-r11 证据

独立复签批次。r10 的 QA 签名由实现方持有私钥执行（业主授权自签），且窗口已过期，
不可作为独立背书；本批次在同一冻结基线上重跑 8 条开发门禁，QA 留 `QA_PENDING`。

- `allowed_holders` 含 `qa-external-02`（holder 名必须与签名 principal 一致，否则 qa-run 报 unknown target holder）
- r10 因本批建批（`loops/*/LOOP.yaml` 属控制面）转为 STALE，属既定不可逆代价
- 载荷必须最后由 QA 侧生成，1 小时内签完并 accept-qa
