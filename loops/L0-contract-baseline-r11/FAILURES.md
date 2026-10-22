# r11 失败登记

（尚无。注意：run_gate 失败一次即消耗一次 attempts，上限 3；不得用真批次试签）

## FAIL-2026-10-22-01 无签名却产生"独立签名"提交

- 现象：提交 `8345e0f` 信息声明 `独立签名 qa-external-02 / qa-ed25519-indep`，
  实际内容仅新增 0 字节 `.runner.lock`；`accept-qa` 因 `/tmp/qa-attestation-r11.json`
  不存在而失败，`manifest` 中 `attestation` 为空。
- 拦截：`finish` 正确拒绝（`DONE requires all gates pass`），r11 未被误标 DONE；
  `baseline_hash` 保持 `4a4bfa74…`，控制面未受影响。
- 处置（2026-10-22 由 QA 执行）：`git reset --mixed HEAD^` 丢弃该提交，HEAD 回到 `9cca157`；
  `.runner.lock` 回到未跟踪。`.gitignore` 补规则延后到签名收口之后
  （`.gitignore` 属控制面，窗口内改动会使锚点失配）。
- 根因：把"生成载荷 / 签名 / accept / finish / commit"多步混在同一段命令里串行执行，
  且 `git add <目录>` 把临时锁文件一并纳入；提交信息在产物不存在时即写下"已完成"。
- 规则：提交信息中的任何"已完成"断言，必须在同一命令块内先验证产物存在
  （`ls -l` 或 manifest 断言），否则不得书写；提交一律用显式文件路径，禁止 `git add <dir>`。
