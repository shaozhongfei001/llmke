# P0-02 仪器：DDL ↔ 资产台账差异清单

日期：2026-10-22　状态：**已实现并用合成夹具验证**
工具：`docs/baseline/validation/p0-02-ddl-diff.py`
性质：只读分析；不修改台账、不修改任何控制面文件；r9 候选不受影响（已复核 PASS）。

---

## 1. 为什么现在做

P0-02 的证据要求是"**实际 DDL 与实体模型的差异清单**"。
当前台账 `docs/reuse/DATABASE-ASSETS.yaml` 的真实状态：

| 项 | 值 |
|---|---|
| 表 | 37 |
| 实体字段合计 | 482 |
| `actual_ddl_sha256` 有值的项 | **0** |
| `baseline.ddl_snapshot_sha256` | `null` |
| `authoritative_status` | `CANDIDATE_ONLY_REQUIRES_SOURCE_OR_DDL` |

即：**台账是候选，缺的就是 DDL**。等 `data-owner` 交出 `SHOW CREATE TABLE` 快照时，
若没有现成工具，就只能人工比对 37 张表——既慢又无法复核。

---

## 2. 它做什么

```bash
python3 docs/baseline/validation/p0-02-ddl-diff.py --ddl /path/to/schema.sql
```

| 检查 | 判定 |
|---|---|
| 表集合 | 台账 37 张 vs DDL 实际 → `MISSING_IN_DDL` / `EXTRA_IN_DDL` |
| 每表列数 | 台账 `model_field_count` vs DDL 列数 → `COUNT_DRIFT` |
| 每表指纹 | 规范化后 sha256，可回填台账 `actual_ddl_sha256`（`--emit-patch`） |
| 引擎/字符集 | 从尾部选项提取（`--dump-columns` 一并显示） |

选项：

| 参数 | 作用 |
|---|---|
| `--ignore-count-drift` | 只把表集合差异判失败；列数漂移仅提示 |
| `--emit-patch` | 输出台账回填片段（**不自动改文件**） |
| `--dump-columns` | 逐表列名与类型，供人工核对语义 |

退出码：`0` 无差异 / `2` 有差异或输入不可解析。

---

## 3. 验证（合成夹具，`/tmp/ddlprobe`）

用台账的 37 表 / 482 字段生成等价 DDL，再逐项破坏：

| 用例 | 期望 | 实测 |
|---|---|---|
| A 完整匹配 | exit 0 | **exit 0**，`缺表=0 多表=0 列数不一致=0` |
| B 删掉一张表 | exit 2 且点名 | **exit 2**，`MISSING_IN_DDL: user_security_question（台账=8）` |
| C 多一张表 | exit 2 且点名 | **exit 2**，`EXTRA_IN_DDL: unknown_table（列数=3）` |
| D 某表多一列 | exit 2 | **exit 2**，`COUNT_DRIFT: answer 台账=15 DDL=16` |
| D2 同上 + `--ignore-count-drift` | exit 0 但提示 | **exit 0**，`1 处列数漂移…仍需人工确认` |
| E 缩进与 CRLF 变体 | 指纹必须相同 | **相同**（`238531b0…` 两者一致） |

E 是关键：`SHOW CREATE TABLE` 的缩进/换行随客户端变化，若原样哈希，
同一张表在两次导出中会得到不同指纹，回填台账后**无法复现**。所以先规范化再哈希。

---

## 4. 它不做什么（不夸大）

| 项 | 原因 |
|---|---|
| 字段类型/长度/默认值/注释 | 台账没有这些基线，没有基线就没有"差异"可判；只能 `--dump-columns` 列出 |
| 索引/约束/触发器 | 台账相应字段全为 `null`（`actual_indexes_constraints_triggers_ref`） |
| 字段语义（`create_by` = 用户 ID / 账号 / 姓名） | 必须人工裁定，这正是 P0-02 的 D-03 |
| 生产同版本兼容性 | 需要恢复副本上实跑，不在静态比对范围 |

换言之：**这个工具产出的是"结构差异清单"，不是"P0-02 已关闭"。**
P0-02 的关闭仍需要 dossier + 逐项回答 + 迁移执行记录 + owner 与 baseline-owner 签名，
由 `p0_closure_check.py --mode strict` 判定（该闸门已通过 14/14 红队审计，见 `P0-GATE-REDTEAM-AUDIT.md`）。

---

## 5. 材料到手后的一条命令

```bash
cd ~/data/dev/llmke-r8
export PATH=~/data/dev/llmke/.venv/bin:$PATH

# 1) 结构差异清单（贴进 P0-02 的 D01 回答）
python3 docs/baseline/validation/p0-02-ddl-diff.py \
  --ddl ~/incoming/prod-schema.sql --dump-columns > /tmp/p0-02-diff.txt

# 2) 台账回填片段（人工确认后再粘，不自动改）
python3 docs/baseline/validation/p0-02-ddl-diff.py \
  --ddl ~/incoming/prod-schema.sql --emit-patch | tee /tmp/p0-02-ledger-patch.txt
```

若第一步是 `FAIL`，那就是本轮要交给 `data-owner` 的具体问题清单，而不是一句"DDL 对不上"。
