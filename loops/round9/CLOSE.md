# ROUND9 关闭记录

- 关闭时间：2026-10-24
- 关闭人：tech-lead（业主指令："完成了就关闭，没完成就继续"）
- 关闭方式：**交付物达成后关闭**，不是"外部条件全满足"

## 一句话

代码与证据交付完成：可运行纵向切片、代次守卫、outbox 语义、`command_digest`（scheme=4）、两份 dry-run 对账、
第十轮 DAG；**四项 P0 仍全 OPEN，业务不可开工**。

## 达成项（对照第九轮 §7）

| 要求 | 结果 |
|---|---|
| 本地可运行纵向切片 + 端到端自动测试 | ✅ `modules/answer_api`（query→授权取块→证据→答案→HTTP），44 条含 5 条真库 |
| 修改文件、提交 SHA、日志、树指纹 | ✅ 账本 14/19 回填；`STATE.tree_sha` |
| 四项 P0 输入表、责任人、已验证输入、阻塞 | ✅ `P0-INPUTS.md` |
| 摘要/信任链缺口的变异测试 | ✅ `T13`（缺口实测）+ `T15`（可行性）+ **scheme=4 落地**（`tests/test_command_digest.py`） |
| owner 包过期数据的修订或保留原因 | ✅ `P0-CLOSURE.baseline_version=1.1.0` 保留并写明理由 |
| r2/r4 归档 + D1–D54/批次/测试统一口径 | ✅ `coordination/round9-index.py`，STATE 与账本一致 |
| 第十轮 DAG、命令、owner 输入清单 | ✅ `ROUND10-INPUTS.md` |

## 未达成项（不结转成"已完成"）

| 项 | 状态 | 事实 |
|---|---|---|
| P0-01 接口 | **OPEN** | 506 条全 `INVENTORY_UNVERIFIED`；运行时证据 0；清单哈希不可复算 |
| P0-02 数据库 | **OPEN** | 仅完成仓内三产物对账（37/478→43/538）；无生产 DDL 与恢复副本 |
| P0-03 权限 | **OPEN** | 实现为候选（fail-closed + SQL 谓词）；E1 规范未批准 |
| P0-04 索引代次 | **OPEN** | 缺 `generation_id`、`claimed_at`；四后端未联调 |

## 候选与门禁

| 项 | 值 |
|---|---|
| 冻结 | `revision 13` / 217 文件 / `1.1.1` |
| 候选 | `L0-contract-baseline-r12`：8 pass + `independent_qa_gate=QA_PENDING`（`scheme=4`） |
| 证据 | `evidence-check r12` **PASS** |
| 门禁 | `make framework-verify` **rc=0 / 303 passed / 0 skipped** |
| 业务闸门 | `make p0-gate` **rc=2** |
| r11 | 因新增代码 STALE（历史候选） |

## 已如实登记的局限

1. **`command_digest` 只覆盖"门禁 argv 里的脚本"**。本轮门禁 argv 是 `make <target>`，闭包为空，
   因此 `docs/baseline/validation/schema-verify.sh` 这类**人工验证命令**仍不在绑定范围内。
   正解二选一：把它移入 `scripts/`，或新增"人工检查登记"（记录 argv + 闭包摘要）。
2. 代次守卫按 `document_version` 对齐，不是按 `generation_id`（缺列）。
3. outbox 用 `next_attempt_at` 兼任可见性超时，无法区分慢消费者与崩溃（至少一次语义）。
4. 独立 QA 仍无签署：`qa-ed25519-indep` 私钥此前已丢失。

## 结转第十轮

见 `ROUND10-INPUTS.md`（8 节点 DAG / 7 项 owner 输入 / 4 条禁令）。

## 复验命令

```bash
cd ~/data/dev/llmke
export PATH=$PWD/.venv/bin:$PATH LLMKE_TRUST_ROOT=$HOME/data/qa-keys/trust-root.json
~/data/dev/coordination/mysql-probe.sh start
make framework-verify > /tmp/fv.log 2>&1; echo "rc=$?"; grep -E "passed|security" /tmp/fv.log | tail -2
~/data/dev/coordination/evidence-check.sh L0-contract-baseline-r12
make p0-gate > /tmp/p0.log 2>&1; echo "rc=$?（期望 2）"
```
