# P0-01 接口清单审计（DRY RUN）

> **status: DRY_RUN · P0-01 仍 OPEN · 不构成"接口已在用"的结论**

输入：`docs/reuse/INTERFACE-ASSETS.yaml`（version 1.1.0）
来源自述：previous review inventory, not runtime routes

## 内部自洽

| 检查 | 结果 |
|---|---|
| 条目数 506 == counts.total 506 | PASS |
| Java/Python 分布 | PASS：{'Java': 440, 'Python': 66} |
| asset_id 重复 | 无 |
| 同服务内 method+path 重复 | 0 组（真冲突） |
| 跨服务同路径 | 3 组（正常，不同实现各自注册） |

## 证据覆盖（关键）

| 维度 | 非空条数 | 占比 |
|---|---|---|
| 运行时证据 | 0 | 0.0% |
| 目标契约 | 0 | 0.0% |
| 兼容决策 | 0 | 0.0% |

状态分布：{'INVENTORY_UNVERIFIED': 506}

## 清单哈希

- 声明：`770eff0506e84ebf2cdfabbb9c3603c0951de26421b32a99bd47bde9310b9206`
- 复算结论：**UNVERIFIABLE**（四种常见归一化均不匹配 ⇒ 无法证明清单未被改动）

## 这批数字能支持什么 / 不能支持什么

**能支持**：存在 506 条候选接口记录，且全部标注为未验证。

**不能支持**：
1. 任何一条"已在生产被调用"——`runtime_evidence` 全空；
2. 任何一条"已确定目标契约"——`target_contract` 全空；
3. 任何一条"保留/废弃已决策"——`compatibility_decision` 全空；
4. 清单来源可信——`inventory_sha256` 不可复算。

因此 `route export`（若将来有）只能证明"注册"，不能证明 `IN_USE`；本条与 P0-01 判据一致。

## 复现

```bash
python3 coordination/p0-01-inventory-audit.py --out /tmp/p001.json --md /tmp/p001.md
```
