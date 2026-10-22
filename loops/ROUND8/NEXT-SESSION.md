# 续跑说明（第八轮已收尾，2026-10-23）

## 状态一句话

**第八轮技术完成、无独立背书，业主裁定就此为止。** 代码/数据/证据无待修项；
业务不可开工（`p0-gate` rc=2，P0-01~04 全 OPEN，L1–L4 BLOCKED）。

## 事实快照

| 项 | 值 |
|---|---|
| HEAD | `4de6bf5`（QA 结论）→ 本文件所在提交 |
| 当前候选 | `L0-contract-baseline-r11`，`QA_PENDING`（未签，且无独立背书） |
| 冻结 | `revision 12` / 215 文件 / `1.1.1` |
| `baseline_sha256` | `4a4bfa74…` == trust-root `anchor` |
| r11 `subject_sha256` | `84251565…`（QA 门禁 14:49:38Z 重跑后） |
| r10 | `DONE` 但九条全 STALE（建 r11 的既定代价，属历史记录） |
| `attempts` | `independent_qa_gate: 2/3`、`module_test_gate: 2/3`，其余 1/3 |
| 私钥 | `~/secure/qa-independent.key` **已 shred，无副本，无交付证据** |

## 若将来要"独立背书"（不要复用 r11）

`attempts` 只剩 1 次，且签名窗口 1 小时——在 r11 上重试风险极高，应新建批次：

1. 第三方**在自己的机器**生成 ed25519，只把 `.pub` 给你（私钥不出门）；
2. 用新公钥**替换** `trust-root` 中 `qa-ed25519-indep` 的 `public_key_pem`；
3. 先做 **custody proof**（`~/data/dev/coordination/verify-custody.sh`），PASS 后才允许删除本地副本；
4. 建新批次（先落 `LOOP.yaml`/计划 → 一次冻结 → 跑门禁 → 留 `QA_PENDING`）；
5. QA 复核完 → **最后一步**生成载荷（1 小时）→ 持钥方签名 → `close-batch.py --execute`。

## 常用命令（规则 R1：不接管道，取退出码）

```bash
cd ~/data/dev/llmke
export PATH=$PWD/.venv/bin:$PATH LLMKE_TRUST_ROOT=$HOME/data/qa-keys/trust-root.json
~/data/dev/coordination/mysql-probe.sh start
make framework-verify > /tmp/fv.log 2>&1; echo "rc=$?"; tail -3 /tmp/fv.log   # 0 / 252 passed 0 skipped
~/data/dev/coordination/evidence-check.sh L0-contract-baseline-r11           # PASS
make p0-gate > /tmp/p0.log 2>&1; echo "rc=$?（期望 2）"
```

## 已立规则（勿再犯）

- 提交信息里写"已完成"前，必须在同一命令块内验证产物存在；`git add` 只用显式路径。
- 载荷/签名/accept/finish 不得混在一个命令块串行执行（见 `FAIL-2026-10-22-01`）。
- `shred` 之前必须先拿到 custody proof（本会话教训，私钥已因此永久丢失）。
- `docs/baseline/validation/` 只放结论，不放可执行补丁（见该目录 `README.md`）。

## 说明

文档中不写宿主绝对路径（写 `~/`），否则 `security-check` 判失败。
