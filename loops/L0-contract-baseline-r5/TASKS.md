# 第三轮任务账本（B 策略）

- 裁决：不合 `fix-window/v1.1.1` 到 `main`；以 `L0-contract-baseline-r5` 为下一目标批次
- 纪律：先改齐控制面 → 一次性冻结 → 再跑门禁 → 独立 QA；不在门禁执行中重冻结

## 1. 任务表

| ID | 目标 | 状态 | 证据 / 说明 |
|---|---|---|---|
| T1 | 修复 T-12 版本一致性 | **DONE** | `docs/baseline/validation/T1-VERSION-REGISTER.md`；逐文件定性，未批量替换 |
| T2-a | P-02 取得 `qa-owner` 语义确认 | **BLOCKED** | 决策包 D-01（`DECISION-PACK-V1.1.1.md`），三选一待选 |
| T2-b | `requirements.lock` 去重 | **BLOCKED** | 决策包 D-02：2 处版本冲突（`pip` 25.0.1/26.2.1、`idna` 3.19/3.20）、14 个无关重型包、105 行/95 唯一包 |
| T3-a | 建立 r5 并一次性冻结 | **DONE** | revision 6、控制面 205 文件、`baseline_sha256=213c6ebc…` |
| T3-b | 跑 7 条开发门禁 + framework-verify + evidence-check | **DONE** | 7/7 pass；exit 0 / 145 passed；evidence-check PASS |
| T3-c | 对抗性检查 3 组 | **DONE** | 控制面变化→7/7 STALE；日志篡改→hash mismatch；文档改动→仅 traceability STALE |
| T3-d | 独立 QA 检查 r5 | **BLOCKED** | `qa-run` 已产出 `QA_PENDING`/`LOCAL_QA_CANDIDATE`；签名未取得，原因见 T4 |
| T4 | 合并到 `main` | **BLOCKED** | 五条件中仅第 1 项满足；第 2 项（QA 允许合并）未满足，故不合并 |

## 2. 合并五条件核对

| # | 条件 | 现状 |
|---|---|---|
| 1 | r5 门禁 + evidence-check 全通过 | **满足** |
| 2 | 独立 QA 对 r5 冻结候选给出允许合并结论 | **未满足** |
| 3 | 拟合并树与 QA 审阅树一致 | 待 QA 签署时锁定树哈希（当前 `HEAD^{tree}` 需在签署后复核） |
| 4 | 合并差异已核对、无未审查提交 | 满足（`main` 是祖先；临时工作树实测合并结果树 == 分支树 `7db46fca…`） |
| 5 | 符合分支保护 | `main` 无保护规则；按约定 `--no-ff`，不强推 |

## 3. 唯一硬阻塞的构成

1. 信任根 `approved_baseline_sha256 = c8a73c37…`（窗口前旧基线），r5 为 `213c6ebc…`
   → 任何签名都会被 `external approved baseline digest mismatch` 拒绝；
2. 由实现者签名或修改信任根 = 自签，独立性失效。

处置与命令：`docs/baseline/validation/R5-QA-HANDOFF.md` §3（由 `qa-owner` 在受保护环境执行）。

## 4. r4 的处置（按裁决保留）

- r4 状态仍为 `IN_DEV`，证据文件**未被删除或覆盖**；
- 因 T-12 改动 + 重冻结，r4 的 `evidence-check` 现在报 STALE —— 这是**正确事实**：
  它的记录绑定 revision 5 的基线，不再代表当前候选；
- 因此 **不得引用 r4 的证据作为 r5 的验收证据**；
- 是否把 r4 显式标为 `SUPERSEDED`（P-06 已支持）留待业主措辞确认，本轮未改其状态。

## 5. 下一条精确命令

```bash
cd ~/data/dev/llmke
~/data/dev/coordination/mk.sh framework-verify                                  # 期望 0
python3 scripts/loop_guard.py evidence-check --loop L0-contract-baseline-r5     # 期望 PASS
~/data/dev/coordination/mk.sh p0-gate                                           # 期望 2（业务仍阻断）
```
