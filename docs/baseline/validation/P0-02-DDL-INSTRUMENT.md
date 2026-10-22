# P0-02 仪器：DDL ↔ 字段明细基线差异清单

日期：2026-10-22（v2：接入字段级基线）　状态：**已用真实基线 + 合成 DDL 验证**
工具：`docs/baseline/validation/p0-02-ddl-diff.py`
基线：`docs/upstream/数据库表结构-字段明细.csv`（482 行，37 表）
性质：只读；不改台账、不改基线、不改控制面；r9 候选不受影响。

---

## 1. 为什么升级（v1 → v2）

v1 只能比"表集合 + 每表列数"，因为当时以为台账只有 `model_field_count`。
后来发现仓内还有**上游字段明细 CSV**（表名 / 字段名 / SQL 类型 / 长度 / 主键 / 自增 / 可空 / 注释 / Java 字段），
这比"列数"强得多：**能把 P0-02 要求的"实际 DDL 与实体模型差异清单"直接算出来**。

| 能力 | v1（列数） | v2（字段级） |
|---|---|---|
| 表集合差异 | ✅ | ✅ |
| 列数差异 | ✅ | ✅（保留为兜底） |
| 列名缺失/多余 | ❌ | ✅ `MISSING_COLUMN` / `EXTRA_COLUMN` |
| 类型/长度差异 | ❌ | ✅ `TYPE_MISMATCH`（`VARCHAR(255)` ≠ `VARCHAR(512)`） |
| 可空差异 | ❌ | ✅ `NULL_MISMATCH` |
| 每表 DDL 指纹 | ✅ | ✅（可回填 `actual_ddl_sha256`） |

---

## 2. 验证（真实基线 + 合成 DDL，`/tmp/ddlprobe`）

合成 DDL 由字段明细 CSV 直接生成（37 表 / 482 字段），再逐项破坏：

| 用例 | 期望 | 实测 |
|---|---|---|
| A 完全一致 | exit 0 | **exit 0**，`字段级比对：基线表=37 发现差异=0` |
| B 删 `answer.id` | exit 2 + 点名 | **exit 2**，`MISSING_COLUMN: answer.id（基线 BIGINT）` |
| C 多一列 `extra_col` | exit 2 + 点名 | **exit 2**，`EXTRA_COLUMN: answer.extra_col（DDL VARCHAR(32)）` |
| D `VARCHAR(255) → 512` | exit 2 | **exit 2**，3 条 `TYPE_MISMATCH`（`log_result`/`reference`/`type`） |
| E `gmt_create` 可空翻转 | exit 2 | **exit 2**，`NULL_MISMATCH: answer.gmt_create 基线 NULL DDL NOT NULL` |
| F 缩进/CRLF 变体（v1 用例） | 指纹一致 | 一致（`238531b0…`），证明规范化有效 |
| G 缺表 / 多表（v1 用例） | exit 2 | 仍为 **exit 2** |

---

## 3. 关键设计

| 设计 | 原因 |
|---|---|
| 类型比较带长度 | `VARCHAR(255)` 与 `VARCHAR(512)` 在生产是不同约束（截断风险），归一成 `VARCHAR` 会把风险藏起来 |
| 指纹先规范化再哈希 | `SHOW CREATE TABLE` 的缩进/换行随客户端变化；原样哈希会让同一张表两次导出得到不同指纹，回填台账后无法复现 |
| 列数漂移降为兜底 | 有字段级基线时，列数不一致必然已被 `MISSING/EXTRA_COLUMN` 捕获；再报一次只会造成噪音 |
| 默认值/注释不比 | 基线里大量为空，比了只会产生"基线缺失"式假差异；`--dump-columns` 里可见，交人工 |

---

## 4. 仍不判定的（不夸大）

| 项 | 原因 |
|---|---|
| 索引 / 约束 / 触发器 / 字符集是否与生产一致 | 台账与 CSV 都没有这些基线 |
| `create_by` 语义（用户 ID / 账号 / 姓名） | 必须人工裁定，这是 P0-02 的 D-03 |
| 迁移脚本可执行性、双版本兼容 | 需在恢复副本上实跑，不在静态比对范围 |
| 字段顺序 | 不同 ORM 允许不同物理顺序，不比 |

**产出是"结构差异清单"，不是"P0-02 已关闭"。** 关闭仍要 dossier + 逐项回答 + 迁移执行记录 +
owner 与 baseline-owner 签名，由已通过 14/14 红队审计的 `p0_closure_check.py --mode strict` 判定。

---

## 5. 材料到手后的一条命令

```bash
cd ~/data/dev/llmke-r8
export PATH=~/data/dev/llmke/.venv/bin:$PATH

# 结构差异清单（D01 回答素材）
python3 docs/baseline/validation/p0-02-ddl-diff.py \
  --ddl ~/incoming/prod-schema.sql --dump-columns > /tmp/p0-02-diff.txt

# 台账回填片段（人工确认后再粘，不自动改文件）
python3 docs/baseline/validation/p0-02-ddl-diff.py \
  --ddl ~/incoming/prod-schema.sql --emit-patch
```

若输出 `FAIL`，那几行就是交给 `data-owner` 的具体问题，而不是一句"DDL 对不上"。
