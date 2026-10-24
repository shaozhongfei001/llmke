# ROUND8 关闭记录

- 关闭时间：2026-10-23
- 关闭人：project-owner（裁定"按 ② 收尾，无独立背书，就此为止"）
- 关闭方式：**业主主动关闭**，不是"全部达成后自然结束"

## 一句话结论

**技术完成、无独立背书。** 代码/数据/证据无待修项；业务不可开工。

补一句边界（外部评审指出）：本轮关闭**不等于该批次满足正常 QA 收口条件**。`independent_qa_gate` 从未取得有效独立签名，r11 仍为 `QA_PENDING`；`CLOSED_WITHOUT_ENDORSEMENT` 只是账本备注，**不是门禁规范中的合法终态**（规范只有 `DONE / SUPERSEDED / RETIRED`）。

## 判定口径（避免后人误读）

"结束"有两种，本文件按第二种：

| 口径 | 本轮 |
|---|---|
| 全部目标达成后自然结束 | **否**（2 项未达成） |
| 业主确认不再投入、明确记录未达成项后关闭 | **是** |

因此：**不得把本轮关闭表述为"第八轮全部完成"**，尤其不得表述为"已通过独立 QA"。

## 达成项（25 / 27）

| 项 | 实测 |
|---|---|
| 框架门禁 | `make framework-verify` rc=0 / **252 passed、0 skipped** |
| schema 落地 | `schema-verify.sh` rc=0 / 43 表 538 列 / 97 模块测试 / C1–C6 全 PASS |
| 候选证据 | r11 `evidence-check` **PASS**（8 pass + `independent_qa_gate=QA_PENDING`，scheme=3） |
| 冻结 | `revision 12` / 215 文件 / `1.1.1`，与 `VERSION` 一致 |
| 证据绑定 | 改实现代码 → 仅 QA 门禁 STALE；控制面加文件 → 9 条全 STALE；改文档 → 仅 traceability；篡改日志 → hash mismatch |

## 未达成项（不结转成"已完成"）

| 任务 | 状态 | 事实 |
|---|---|---|
| `R8-T04` 独立 QA 签署 | `CLOSED_WITHOUT_ENDORSEMENT` | 技术复核 PASS 但**未出具签名**：`qa-ed25519-indep` 私钥已 shred、无副本、无交付证据 → 公钥悬空，永久无法签名 |
| `R8-T05` 真实 DDL / 路由 / E1 / S1–S5 | `BLOCKED_EXTERNAL` | 对应 owner 未提供；**随轮次结转下一轮**，不得视为已解决 |

## 业务闸门（未因本轮关闭而改变）

- `make p0-gate` → **rc=2**
- P0-01 / P0-02 / P0-03 / P0-04 **全部 OPEN**
- L1–L4 **BLOCKED**，业务**不可开工**

## 计数口径（外部评审指出原文有混淆，已更正）

| 项 | 正确值 | 说明 |
|---|---|---|
| `SUPERSEDED` 批次 | **6 个**（r3、r5、r6、r7、r8、r9） | 其中**本轮内作废 5 个**（r5–r9）；r3 属本轮回溯前的历史遗留 |
| 决策记录 | **53 条**，编号 D1–D54 | **缺 D47**（未使用），不是 54 条 |
| r9 → r10 替代原因 | **未记录** | 决策记录无对应条目，仅存提交信息；属流程缺陷，不推断原因 |
| 本轮任务 | 27 | 25 VERIFIED / 1 `CLOSED_WITHOUT_ENDORSEMENT` / 1 `BLOCKED_EXTERNAL` |

## r10 必须分三列（合并表述会误读）

| 维度 | 值 |
|---|---|
| 历史执行状态 | `DONE`（曾被接受并合并） |
| 当前证据有效性 | **九条全 STALE**（建 r11 后 `control_digest` 变化） |
| 独立签署状态 | **无**（实现方持钥自签，且签名已于 `2026-10-22T06:47:14Z` 过期） |

结论：只有第一列表示"曾经发生过"；后两列均为否，**不得合并写成"r10 已完成"**。

## 结转与后续

1. `R8-T05` → 下一轮首要输入，依赖四位 owner 的材料。
2. 若将来要独立背书：**不要复用 r11**。原因有二：`attempts` 中 `independent_qa_gate` 已用 2/3（再失败即耗尽），签名窗口固定 1 小时。正确顺序见 `NEXT-SESSION.md`。
3. `trust-root` 中 `qa-ed25519-indep` 为**悬空登记**（公钥在册、私钥不存在）。是否清除由业主决定，清除属 trust-root 改动、不影响基线。

## 复验命令（规则 R1：不接管道）

```bash
cd ~/data/dev/llmke
export PATH=$PWD/.venv/bin:$PATH LLMKE_TRUST_ROOT=$HOME/data/qa-keys/trust-root.json
~/data/dev/coordination/mysql-probe.sh start
make framework-verify > /tmp/fv.log 2>&1; echo "rc=$?"; tail -3 /tmp/fv.log
~/data/dev/coordination/evidence-check.sh L0-contract-baseline-r11
# 最近一次 252/0 的完整日志：docs/baseline/validation/ROUND8-FRAMEWORK-VERIFY-252.txt
make p0-gate > /tmp/p0.log 2>&1; echo "rc=$?（期望 2）"
```
