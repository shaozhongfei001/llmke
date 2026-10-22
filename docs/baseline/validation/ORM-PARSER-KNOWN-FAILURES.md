# ORM 解析器：保留的失败样例（不删除）

> A3 要求「保留失败样例，禁止只保留修正后的绿测」。
> 本文件保存**修复前会失败**的样例与其实际错误输出，供后人验证修复是否真的必要。

- 工具：`loops/LD-legacy-discovery/tools/orm_parser_selftest.py`（当前 **8/8 PASS**）
- 复现：`python3 loops/LD-legacy-discovery/tools/orm_parser_selftest.py`

---

## FAIL-1 `association` 内嵌列被计入父表（已修）

**修复前实测**：`parent=['id','name']`（`kb_name` 被当成父表列）
**正确行为**：`parent=['id']`，`nested=['kb_name']`
**危害**：父表覆盖率**虚高**；若按此判断"列已知"，会把子表列错认成父表列。

## FAIL-2 `collection` 内层 property 覆盖外层主键（已修）

**修复前实测**：`parent=['file_id']`（外层 `id` 丢失）
**正确行为**：`parent=['id']`，`nested=['file_id']`
**危害**：主键列消失，覆盖率**虚低**；更糟的是「主键不存在」这种结论会被写进报告。

## FAIL-3 同名 property 静默丢列（已修）

**修复前实测**：`{createBy: creator}`（`create_by` 被覆盖）
**正确行为**：`{createBy: create_by}` + `conflicts=[{kept: create_by, dropped: creator}]`
**危害**：真实列名丢失且**无任何提示**——这是三类里最隐蔽的。

## FAIL-4 同名实体文件静默取首个（已修）

**修复前**：`find()` 直接返回 `hits[0]`，无提示。
**实测命中**：`DB-34 user_operate` 有两个 `UserOperateDO.java`
（`ragauthservice/domain/model/` 与 `ragcommon/operation/model/`，字段均 12 个、内容不同）。
**修复后**：`find_report()` 返回全部命中，覆盖率工具写入 `ambiguous_entity_or_mapper`。
**危害**：读错文件会让该表所有字段结论失真，且不会报错。

## 仍存在的盲区（未修，明确保留）

| 盲区 | 表现 | 为什么不修 |
|---|---|---|
| SQL 别名 | `SELECT a.create_by AS creator` 的列名不在 resultMap，解析不到 | 需解析 SQL 语义，超出映射层；已由 B1 的 SQL 引用索引覆盖一部分 |
| Java 继承 | 不读 `extends`，父类属性无法区分 | 实测 37 表 `extends` 全为空，当前无影响 |
| `SELECT *` | 列完全不在文本中 | 已单独标记，本次 0 处命中目标表 |
| MyBatis-Plus 注解实体 | 无 XML SQL，覆盖率记为 `NO_MAPPER`/`NONE` | 已通过 `mapping_mode=MP_BASEMAPPER` 单独标识，不再误判 |

---

## 使用说明

- 这些失败样例**不是待办**，而是**回归基线**：任何一次解析器改动后，应能复现"修复前的错误输出"，
  以确认修复没有被后续改动悄悄回退。
- 复现修复前行为的方法：把 `parse_resultmap_block` 的 depth 跟踪去掉（内嵌列即回落到父表）。
