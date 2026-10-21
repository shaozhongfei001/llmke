# B4：ORM 覆盖率的定义、验证样例与解析边界

- 工具：`tools/db_orm_coverage.py`（统计）、`tools/db_mapper_columns.py`（解析）、
  `tools/orm_parser_selftest.py`（样例自检，**6/6 PASS**）
- 目的：让「14 FULL / 17 PARTIAL / 3 NONE / 3 NO_MAPPER」这个数字**可被人工复核**，
  并说清它到底证明了什么、没证明什么

---

## 1. 覆盖率的口径（精确到分母）

| 概念 | 定义 |
|---|---|
| 分母 | 该表 DO 实体中 `private` 非 `static` 字段的个数（不含 `serialVersionUID`） |
| 分子 | `resultMap` 中 `column` 值，经驼峰转下划线后**命中分母字段**的个数 |
| `FULL` | 分子 == 分母 |
| `PARTIAL` | 0 < 分子 < 分母 |
| `NONE` | 找到 mapper 文件，但其中**没有 `resultMap`**（纯手写 SQL） |
| `NO_MAPPER` | 按 `实体名-Mapper.xml` 找不到 mapper 文件 |
| `NO_ENTITY` | 找不到 DO 文件 |

**输入范围**：`RAG-SRC/_src` 下 `gien-rag/**` 的 DO 与 `src/main/resources/mapper/*.xml`。
**不含**：Service/Repository 层注解、MyBatis-Plus 的 `BaseMapper` 默认方法、其他服务的 DAO。

## 2. 六个可人工核对的样例（全部实测通过）

| 样例 | 覆盖写法 | 期望 | 实测 |
|---|---|---|---|
| F1 | `<id>` + `<result>`，column 在前 | `{id, create_by}` | **PASS** |
| F2 | property 在前、column 在后 | `{id, kb_id}` | **PASS** |
| F3 | `association` 嵌套 | `{id, kb_name}` | **PASS（但属风险，见 §3）** |
| F4 | `collection` 嵌套 | `{file_id}` | **PASS（主键列丢失，见 §3）** |
| F5 | 手写 SQL + 别名 | `{}` | **PASS（不在 resultMap，解析不到）** |
| F6 | 同名 property 两条映射 | `{creator}` | **PASS（先出现的列被覆盖）** |

## 3. 三个已实测的风险（比「漏解析」更危险）

| # | 现象 | 后果 | 对覆盖率数字的影响 |
|---|---|---|---|
| R1 | `association` 内嵌列被计入**父表** | 子表列被误判为父表列 | 可能**虚高**父表覆盖 |
| R2 | `collection` 内层 `property` 与外层同名（如 `id`）时覆盖外层 | 外层主键列**丢失** | 可能**虚低** |
| R3 | 同名 `property` 两条映射，后者覆盖前者 | 先出现的列（常见 `create_by`）丢失 | 可能**虚低** |

**影响评估**：R1/R2/R3 都出现在「嵌套或重复映射」的 mapper 上。
本次 37 张表的 mapper 中未见 `association`/`collection`（样例只用于验证解析器行为），
因此**当前 14/17/3/3 未受 R1/R2 影响**；R3 是否命中需逐文件核对，暂记为 `UNKNOWN`。

## 4. 这个数字**不能**说明什么

| 不能说明 | 原因 |
|---|---|
| 数据库列清单完整 | `resultMap` 是查询所需列的子集；`FULL` 只表示「DO 的字段都有映射」 |
| 列存在性 | 无映射 ≠ 列不存在（第五轮已证：漏的集中是 `isDel`/审计列） |
| 索引、约束、触发器、引擎、字符集 | 完全不可见 |
| 实体字段与列一一对应 | R3 会丢列；别名会隐藏真实列名 |
| 其他服务对该表的访问 | 只扫了 `gien-rag` 的 mapper |

## 5. 结论的正确表述

> **在 `gien-rag` 的 mapper 范围内，37 张表中有 14 张的 `resultMap` 覆盖了其 DO 的全部字段。**
> 这是**映射完整度**，不是**表结构完整度**；38% 只是下界，且不构成 P0-02 的任何关闭依据。

## 6. 遗留盲区（若要提升覆盖率可信度，按此顺序补）

1. 解析 `association`/`collection` 的**归属**（R1）——目前会污染父表；
2. 处理同名 `property` 的覆盖（R3）——目前静默丢列；
3. 识别 MyBatis-Plus `BaseMapper` 实体（无 XML 但有注解）——目前记为 `NO_MAPPER`；
4. 识别 `SELECT *` 的表——目前完全不可见（B1 已单独标记，本次 0 处命中目标表）；
5. 识别继承字段——四张目标表无继承，其余表未全查。
