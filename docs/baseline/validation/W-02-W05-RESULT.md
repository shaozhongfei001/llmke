# 窗口结果：弃 r7 → 应用补丁包（W-05 / W-05b / W-02 / W-04）

日期：2026-10-22　工作树：`~/data/dev/llmke-r8`（`round8/delivery`）
裁决：业主决定**放弃 r7**，直接应用已验证补丁包。
执行：`~/data/dev/coordination/window-apply.sh`（仓外执行器，已隔离验证）。

---

## 1. 结论

| 项 | 结果 |
|---|---|
| 门禁数 | **8 → 9**（新增 `module_test_gate`） |
| 当前候选 | **`L0-contract-baseline-r9`**，8/8 开发门禁 `pass`（`digest_scheme=3`） |
| QA | **QA_PENDING / LOCAL_QA_CANDIDATE**（未签名，不得称通过） |
| `framework-verify` | **exit 0 / 194 passed**（原 193，+W-04 测试） |
| `p0-gate` | **exit 2**（四项 P0 仍 OPEN，L1–L4 BLOCKED） |
| 冻结 | `revision=10`、控制面 **211** 文件、`1.1.1` |
| 执行环境 | 门禁在 `env -i PATH=/usr/bin:/bin` 下跑（证明 W-05b 生效） |

---

## 2. 落地内容

| 项 | 内容 |
|---|---|
| **W-05** | `Makefile` 增 `LLMKE_PYTHON`/`PY`，`@python3`→`@$(PY)` 25 处；新增 `module-test`、`python-info` |
| **W-05b** | 新增 `scripts/_pin.py`（仅标准库）：入口自钉，`run_batch`/`loop_guard` 首个导入 |
| **W-02** | `GATE-CATALOG.yaml` 增 `framework.modules`；批次增第 9 条门禁 `module_test_gate` |
| **W-04** | `tests/test_loop_guard.py` 增「签名有效但候选过期必须被拒」 |
| **授权留痕** | `BASELINE-AUTHORITY.yaml` 的 `change_list` 增 `W-02-W05`（含 `approved_by`） |

---

## 3. 验证

### 3.1 门禁（坏 PATH 下）

```
pass × 8 —— contract_generate / contract_check / mutation_probe / traceability /
            p0_register / security_scan / baseline / module_test
DEV_SELF_CHECK complete; independent QA remains PENDING
```

### 3.2 四条对抗（r9，候选已生成）

| 动作 | 结果 |
|---|---|
| 业务代码加一行注释 | **FAIL: independent_qa_gate: implementation code changed; evidence STALE**（exit 1） |
| `contracts/` 加一个文件 | **9/9 STALE** + `frozen control file set changed` |
| `docs/` 加一个文件 | **仅 `traceability_gate`** STALE |
| 证据日志追加一行 | `baseline_gate: evidence hash mismatch` |
| 复原后 | `evidence-check: PASS` |

> 关键顺序：**必须先生成 QA 候选再做"改代码"对抗**。r8 首次测试时还没有候选记录，
> 改代码自然是 PASS——这是"没有记录绑定代码"，不是"绑定失效"。
> 我第一次就得出了错误结论，重做后才纠正，记录在此以免复现。

### 3.3 W-04 测试有效性

隔离树变异：删掉 `accept_qa` 的 stale 检查 → 新用例**失败**；恢复后 15 passed。

---

## 4. 批次处置

| 批次 | 状态 | 说明 |
|---|---|---|
| r5 / r6 | `SUPERSEDED` | 早期候选（W-01 前 / W-01b 前） |
| **r7** | **`SUPERSEDED`** | 业主弃用，补丁包一并上线，省一次 QA |
| **r8** | **`SUPERSEDED`** | **我的疏漏**：`change_list` 未记录本次变更，授权留痕不完整；趁未签名先补录，故作废重建 |
| **r9** | **`QA_PENDING`** | 当前候选，9 条门禁 |

r5–r8 的证据与日志**原样保留**，未删除、未改写，仅状态转终态。

---

## 5. 候选指纹（r9）

| 项 | 值 |
|---|---|
| `baseline_sha256` | `cf8a72c845ad7fd9052b3e4919688da714aeb990bbbf65280b50e196d719d972` |
| `subject_sha256` | `13754a8bc16700d22081b284ffdf2ce9d5ba1d8aee9f12da72ce3743b91e8d67` |
| `source_sha256` | `4cb3d236d2c3a019498a16fb65eadf89271e69cfa098a5cfdec46cd49ba7c27d` |
| QA 载荷 | `docs/baseline/validation/qa-payload-r9.json`（1 小时有效期，签署前重生成） |

---

## 6. 未关闭项

| 项 | 状态 | 责任方 |
|---|---|---|
| r9 独立 QA 签名 | **BLOCKED** | `qa-owner`（信任根锚点需指向 `cf8a72c8…`；实现者不得自签） |
| P0-01…P0-04 | **OPEN** | interface / data / security / index-owner |
| P-02 语义 | BLOCKED | `qa-owner` |
| `requirements.lock` | BLOCKED | `baseline-owner` |

---

## 7. 回退

未提交时：`git checkout -- .` + `rm -rf loops/L0-contract-baseline-r9`。
已提交时：`git revert` 后必须**再冻结一次**并把 r9 置终态——`run_batch` 拒绝在 STALE 批次上重跑。
