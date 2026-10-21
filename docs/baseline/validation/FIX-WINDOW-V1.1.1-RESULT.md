# 受控变更窗口 V1.1.1 实施结果

- 分支：`fix-window/v1.1.1`（自 `main@4b1fca8` 开出，**未合并**）
- 授权：`docs/baseline/BASELINE-AUTHORITY.yaml`（业主批准 P-01/P-03/P-04/P-05/P-06 进入窗口；P-02、锁文件不在本次范围）
- 本文件位于 `docs/baseline/validation/`（不参与源码快照，也与冻结控制面无关）
- 基线标识：`baseline_version=1.1.1`、`manifest_revision=2`、`frozen_at` 见 `FROZEN-MANIFEST.json`

## 1. 改了什么（逐项可核对）

| 提案 | 文件 | 改动 | 是否削弱门禁 |
|---|---|---|---|
| P-01 | `scripts/security_scan.py` | `loops/*/evidence/*.log` 豁免 `PERSONAL_ABSOLUTE_PATH`；**凭据/连接串/私钥/生产主机规则不豁免**；输出 `evidence_logs_personal_path_skipped=N` | 否（放宽面被显式计数，且不含凭据类） |
| P-03 | `scripts/baseline_support.py`、`scripts/loop_guard.py` | 新增 `control_digest` / `doc_digest`；STALE 判定改用 control；仅 `traceability_gate` 额外比 doc；旧记录无 `digest_scheme` 时保持整树语义 | 否（控制面变化仍判 STALE；只去掉「说明文档」这一非输入项） |
| P-04 | `scripts/freeze_baseline.py`、新增 `docs/baseline/BASELINE-AUTHORITY.yaml` | 冻结元数据外置；缺失/字段不全即**拒绝写入**；写入 `frozen_at` 与自增 `manifest_revision` | 否（更严：不再允许硬编码文案） |
| P-05 | `VERSION`、`BUILD-INFO.txt`、`scripts/freeze_baseline.py` | 版本 1.1.1；冻结脚本版本号改为读 `VERSION` | 否 |
| P-06 | `scripts/loop_guard.py` | 新增 `SUPERSEDED`/`RETIRED`：拒绝执行门禁与 `finish`，不参与 STALE 判定，历史证据保留 | 否（只影响状态机与历史判定） |

新增测试（18 条）：`tests/test_digest_scope.py`（6）、`tests/test_terminal_states.py`（5）、`tests/test_freeze_authority.py`（5），以及 `tests/test_security_scan.py` 增 3 条正反例。
另修正两处测试夹具（`tests/fixture_helpers.py`、`tests/test_closure_and_readiness.py`）：重冻结现在要求 `VERSION` 与授权文件。

## 2. 实测结果（本窗口实跑）

| 命令 | 退出码 | 结果 |
|---|---|---|
| `pytest tests/ -q` | 0 | **145 passed**（窗口前 127，新增 18） |
| `make framework-verify` | **0** | generate/check 各 18 contracts PASS、rule-mirror PASS、trace-check PASS、p0-check(integrity) PASS、security-check **PASS(474 文件, 跳过计数=0)**、145 passed、baseline PASS |
| `make p0-gate` | **2** | 四项 P0 仍 OPEN，**正确阻断** |
| `run_batch --loop L0-contract-baseline-r4` | 0 | 7 条开发门禁全 pass |
| `evidence-check --loop L0-contract-baseline-r4` | 0 | PASS |
| `evidence-check --loop L0-contract-baseline-r3` | 0 | PASS（终态不判 STALE） |

## 3. 两个决定性验证（这是窗口的核心价值）

### 3.1 P-03：文档改动不再整体作废证据

```text
$ echo 说明性文档 > docs/WINDOW-PROBE.md
$ python3 scripts/loop_guard.py evidence-check --loop L0-contract-baseline-r4
FAIL: traceability_gate: dependent documents changed; evidence STALE      → exit 1
$ rm docs/WINDOW-PROBE.md
$ python3 scripts/loop_guard.py evidence-check --loop L0-contract-baseline-r4
evidence-check: PASS (L0-contract-baseline-r4)                            → exit 0
```

- 结果：只有**声明依赖文档**的 `traceability_gate` 失效，其余 6 条保持有效。
- 对比旧行为：任何 `docs/**` 改动 → 7 条全部 STALE（这正是反复返工、耗尽预算的根因）。

### 3.2 P-06：终态批次不再永久卡死

`L0-contract-baseline-r3` 在实施中被误置于「门禁执行中间重冻结」的处境：3 条已通过记录绑定旧基线。
**处理方式：不改写任何历史记录**，将其置为 `SUPERSEDED` + `replaced_by: L0-contract-baseline-r4` + `terminal_reason`，
随后 `evidence-check` 正常 PASS（历史结论保留，不再要求与当前候选绑定），门禁执行被拒。

> 这是缺陷的真实复现，不是人为演示：它证明「重冻结必须一次性收口」这条纪律，也已写入第 6 节。

## 4. 影响面与旧证据处理

| 项 | 影响 |
|---|---|
| `baseline_sha256` | `c8a73c37…` → **新值**（重冻结必然改变） |
| `source_snapshot` | `d0530bee…` → 新值 |
| 控制面文件数 | 198 → **202**（+BASELINE-AUTHORITY、+r3/r4 的 LOOP.yaml、+3 个测试文件） |
| `main` 分支 | **未受影响**：仍在 `4b1fca8`，其 L0-r2 与 LD-r2 证据保持原样 |
| 已签 QA | `LD-legacy-discovery-r2` 的签名绑定旧基线，合并后即失效；按业主口径**作为历史记录保留**，不得冒充当前候选的有效 QA |

## 5. 迁移与回退

- 迁移：本窗口是独立分支，`git checkout main` 即完全恢复旧基线；合并前需完成第 6 节的批次重跑与重签。
- 回退：`git revert` 本窗口提交后，必须 `python3 scripts/freeze_baseline.py --write` 重新冻结一次（因为控制文件内容回退）。
- 回退不得删除 `loops/*/evidence/**`（历史证据 append-only）。

## 6. 合并前必须先做的事（顺序不可颠倒）

1. **一次性**建齐合并后需要的批次（含 LD 侧替代批次）→ 登记 `docs/PROJECT-PLAN.yaml`；
2. 最后**唯一一次**重冻结（此后不得再改 `scripts/**`、`docs/policies/**`、`tests/**`、`loops/*/LOOP.yaml`）；
3. 在新冻结面上按批次顺序跑门禁（每批次无历史记录 → 不会触发「prior evidence invalid」）；
4. 外部独立 QA 在固定快照上复跑并签名；L0 侧只能由 `qa-owner` 签，TL 不得自签；
5. 旧批次置 `SUPERSEDED`（不得删除其 evidence 与 attempts）。

> 本窗口已实测：**在门禁执行中间重冻结，会使该批次已通过的记录全部绑定旧基线，从而卡死该批次**（见 3.2）。

## 7. 未做（明确排除，不得当成已完成）

| 项 | 原因 | 归属 |
|---|---|---|
| P-02（QA 接受时点与复核分离） | 涉签名有效性语义，须 `qa-owner` 书面确认；且历史记录需回填 `accepted_at` | qa-owner |
| `requirements.lock` 去重 | 属依赖基线变更，须 `baseline-owner` 批准 | baseline-owner |
| 合并到 `main`、批次重签 | 需第 6 节全套动作 + 外部 QA | 业主/qa-owner |
| PDF 解析等价性 | 与本窗口无关；`61 passed` 不等于 LLMKE 集成等价 | tech-lead |

## 8. 精确复现命令

```bash
cd ~/data/dev/llmke
git checkout fix-window/v1.1.1
~/data/dev/coordination/mk.sh framework-verify     # 期望 0
~/data/dev/coordination/mk.sh p0-gate              # 期望 2
python3 scripts/loop_guard.py evidence-check --loop L0-contract-baseline-r4   # 期望 PASS
python3 scripts/loop_guard.py evidence-check --loop L0-contract-baseline-r3   # 期望 PASS（终态）
```

## 9. 声明

本窗口只修「证据与状态机制」，**不产生任何业务交付**：四项 P0 仍 OPEN，L1–L4 仍 BLOCKED，`p0-gate` 仍 exit 2。
门禁的 pass 条件未被放宽，被放宽的只有「说明文档是否算作候选输入」这一项非契约判定。
