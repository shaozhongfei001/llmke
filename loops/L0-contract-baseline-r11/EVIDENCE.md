# L0-contract-baseline-r11 证据

独立复签批次。r10 的 QA 签名由实现方持有私钥执行（业主授权自签），且窗口已过期，
不可作为独立背书；本批次在同一冻结基线上重跑 8 条开发门禁，QA 留 `QA_PENDING`。

- `allowed_holders` 含 `qa-external-02`（holder 名必须与签名 principal 一致，否则 qa-run 报 unknown target holder）
- r10 因本批建批（`loops/*/LOOP.yaml` 属控制面）转为 STALE，属既定不可逆代价
- 载荷必须最后由 QA 侧生成，1 小时内签完并 accept-qa

## 独立 QA 复核结论（2026-10-23）

- 结论：**技术复核 PASS；未出具独立签名，r11 保持 `QA_PENDING`。**
- 实测（QA 独立复跑，非转述）：
  - `make framework-verify` rc=0，`252 passed`、0 skipped（副本复跑 75.71s；门禁日志 70.04s）
  - `schema-verify.sh` rc=0，43 表 / 538 列 / `97 passed` / 体检 C1–C6 全 PASS、0 处不一致
  - `p0-gate` rc=2（P0-01~04 全 OPEN，符合预期）
  - 对抗组 4/4 按要求失效：改实现代码→仅 QA 门禁 STALE；控制面加文件→9 条全 STALE；
    改文档→仅 traceability；篡改日志→`evidence hash mismatch`；还原后 PASS
  - 绑定：`digest_scheme=3`、`code_sha256=19517fe1…`、`subject_sha256=84251565…`（复算一致）、
    `baseline_sha256=4a4bfa74…` == trust-root anchor、`FROZEN-MANIFEST` rev=12 / 215 files / 1.1.1
- 未出具签名的原因：`qa-ed25519-indep` 私钥未在本机，亦未由第三方持有并交付；
  `trust-root` 虽已登记该公钥（指纹 `85055cca…`），无对应私钥即无法产生可被验签的载荷。
- 影响边界：本结论**不构成独立背书**，不得表述为"已通过独立 QA"。
  技术层面无代码/数据/证据待修项；`p0-gate` 仍 exit 2，业务不可开工。
- 未做且不应由实现方或 QA 代做：私钥交付。若需独立背书，须由第三方生成并持有密钥后重新签名。
