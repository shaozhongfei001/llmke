# 续跑说明（只写可执行信息）

更新时间：2026-10-22（R11 建立后）

## 现状一句话

工程侧**已无 READY 项**；轮次**未结束**——卡在独立 QA 签署与四项 P0，不是卡在代码。

## 仓库与候选

- 仓库：`~/data/dev/llmke`，分支 `main`
- 当前候选：`L0-contract-baseline-r11`，`QA_PENDING`，holder=`qa-external-02`
- 冻结：`revision 12` / 215 文件 / `1.1.1`
- `baseline_sha256 = 4a4bfa74567fe6cc972a0f8063a60192f9c3c2f8e93a3d74fc17abaecd5d38b8`
- r11 `subject_sha256 = ba580f7d22e04cbb61b82d62870b078a7faaed4c6b5e097b14af43e51aef1ae1`
- r10：`DONE` 但九条全 STALE（建 r11 的既定代价，属历史记录，不得再引用为"当前有效"）

## 下一条准确命令（规则 R1：不接管道，取退出码）

```bash
cd ~/data/dev/llmke
export PATH=$PWD/.venv/bin:$PATH LLMKE_TRUST_ROOT=$HOME/data/qa-keys/trust-root.json
~/data/dev/coordination/mysql-probe.sh start          # 不启会 29 skipped
make framework-verify > /tmp/fv.log 2>&1; echo "rc=$?"; tail -3 /tmp/fv.log   # 期望 0 / 252 passed 0 skipped
~/data/dev/coordination/evidence-check.sh L0-contract-baseline-r11           # 期望 PASS
make p0-gate > /tmp/p0.log 2>&1; echo "rc=$?（期望 2）"
```

## 未完成的两项（都是外部阻塞）

| 任务 | 阻塞 | 需要谁 |
|---|---|---|
| R8-T04 | 独立 QA 签署 r11 | 业主生成**新**密钥并登记 `qa-external-02`；更新锚点为 `4a4bfa74…`；私钥交第三方 |
| R8-T05 | 真实 DDL / 运行时路由 / E1 / S1–S5 | 对应 owner |

注意：本机 `qa-ed25519-2026-10` 已被实现方使用过（**已污染**），不得转交充作独立主体。

## 顺序约束（颠倒即失败，r3/r6 已翻车两次）

1. 任何控制面改动（`scripts/`、`docs/policies/`、`loops/*/LOOP.yaml`、`docs/PROJECT-PLAN.yaml`）
   都会让 r11 立即 STALE；
2. 必须改时：先落全部改动 → **一次**冻结 → 再跑门禁，且必须新建批次（`run_batch` 拒绝在失效批次上重跑）；
3. 载荷**最后一步**生成（`qa_payload.py` 固定 1 小时）→ 立即签名 → `accept-qa`。

## 禁止事项

- 不得自签、不得改 trust-root、不得改 `implementation_principals`；
- 不得把 r10 的 QA `pass` 表述为独立背书；
- 不得在 `docs/baseline/validation/` 放可执行补丁（见该目录 `README.md`）。

## 说明

文档中不写宿主绝对路径（写 `~/`），否则 `security-check` 判失败。
