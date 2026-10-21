# P0-02：D-01 定案（共库）与 D-02 基线（从 ORM 生成候选 DDL）

日期：2026-10-22　性质：分析 + 生成物；不改源码、不改控制面
业主决定：**D-01 选「共库」**
工具：`p0-02-entity-extract.py`、`p0-02-ddl-generate.py`、`p0-02-ddl-diff.py`

---

## 1. D-01 选「共库」的含义

| 项 | 含义 |
|---|---|
| 9 张跨服务表 | **不拆**。`department_info`/`dept_privilege`/`group_privilege`/`user_group`/`user_privilege` 继续被 rag-index-service 直接读；`knowledge_base`/`model_info`/`search_config`/`tools_database` 继续被 rag-auth-service / rag-index-service 直接读 |
| 迁移策略 | 只需"结构同步 + 增量建表 + 加列"，不需要拆共享写、不需要双写窗口 |
| 仍需处理 | `user_operate` 有**两个 DO 定义**（auth 显式 `@Column` 12 处 / common 隐式驼峰 0 处）。共库下两套映射会长期共存，任一侧改动另一侧不报错 —— 这是"共库"方案里唯一必须自己收口的点 |
| 与 5.3 的矛盾 | 设计文档 5.3 步骤①说"用现有 37 表 DDL 初始化新库"、④又说"共用原库"。选共库后，**① 需要修正为"校验现有结构"而非"初始化新库"**；这条应写回设计文档 |

---

## 2. D-02：真实 DDL 在材料里**不存在**（这是实测，不是推测）

按业主要求查了三处：

| 查询位置 | 结果 |
|---|---|
| RAG 源码树（`RAG-SRC/_src/gien-rag`） | **0 个 `.sql` 文件** |
| `~/data/workbuddy_ws/graphrag` 下 20+ 份 `.docx` | `CREATE TABLE` 出现 **0 次**（"DDL"一词出现 4 次，均为"DDL 原样复用"这类表述） |
| `数据库表结构.xlsx`（评审包/03-数据资产） | 四个 sheet：说明 / 表清单(38 行) / 字段明细(483 行) / 待补充(14 行) —— 与仓库里的 CSV **同源**，不含建表语句 |

而设计文档 5.1 写"37 张表 DDL 原样复用"、5.3 写"用现有 37 表 DDL 初始化新库"。
**"原样复用"的对象不存在**，这正是 P0-02 登记里那条"材料中没有 `SHOW CREATE TABLE` 快照"。

---

## 3. 因此：从 ORM 生成候选 DDL

```bash
python3 docs/baseline/validation/p0-02-ddl-generate.py \
  --src ~/data/repo/RAG-SRC/_src/gien-rag/gien-rag/rag-parent \
  --out /tmp/entity-schema.sql
```

产出：**37 张表 / 479 列 / 667 行 SQL**，含类型（带长度）、`NOT NULL`、`AUTO_INCREMENT`、
`DEFAULT`、列注释、主键、表注释、`ENGINE=InnoDB DEFAULT CHARSET=utf8mb4`。
文件头明确标注"由 ORM 注解生成，不是生产快照"，避免被当成真实 DDL 引用。

### 回环验证

| 验证 | 结果 |
|---|---|
| 生成 DDL ↔ 实体基线（`--fields-csv /tmp/entity-model.csv`） | **PASS，0 差异** |
| 四类负例（缺列/多列/类型变更/可空翻转） | 仍全部 **exit 2**（未放水） |

同表多实体的处理：`user_operate` 保留**显式 `@Column` 更多**的那份（auth），
并在输出里 `WARN` 说明被忽略的另一份——不合并，避免产生重复列和下游幽灵差异。

---

## 4. 顺手证实：设计文档 5.1 的索引有一条**建不出来**

5.1 要求补三类索引：

| 索引 | 列 | 实体模型里是否存在 | 结论 |
|---|---|---|---|
| `dialogue.idx_gmt_create_user` | `user_id, gmt_create` | `dialogue` 共 **13 列**，**无 `user_id`**，只有 `create_by` | **建不出来** |
| `file_parse_task.idx_status_create` | `status, gmt_create` | 两列均存在（16 列中） | 可建 |
| `answer.idx_dialogue_id_type` | `dialogue_id, type` | 两列均存在 | 可建 |

`dialogue` 实际列：`id / label / session_id / status / gmt_create / gmt_modified / create_by /
update_by / sys_type / config / config_id / config_history / kb_id`（13 列）。

也就是说：若按文档"建 `(user_id, gmt_create)` 索引"，MySQL 会直接报 `Unknown column 'user_id'`。
**这条与 P0-02 登记的事实完全一致，现在有了机器证据。**
可行的替代是按 `create_by`（账号）建：`(create_by, gmt_create)`——但那是**按账号分页**，
与"按用户（ID）分页"语义不同，必须由 `data-owner` 确认口径后再定。

---

## 5. 还需要 `data-owner` 提供的（精确到格式）

本工具能给出"代码要求的 DDL"，但**给不出生产的真实索引/引擎/字符集**。需要：

```sql
-- 对 37 张表逐张执行，输出原样文本
SHOW CREATE TABLE `answer`;
SHOW CREATE TABLE `dialogue`;
... （37 张）
-- 以及
SELECT VERSION();
SHOW VARIABLES LIKE 'character_set_database';
SHOW VARIABLES LIKE 'collation_database';
```

拿到后：

```bash
python3 docs/baseline/validation/p0-02-ddl-diff.py \
  --ddl <prod-schema.sql> --fields-csv /tmp/entity-model.csv --dump-columns
```

输出的差异即 D-01 的回答素材（表.列 + 两侧类型 + 源码行号）。

---

## 6. 推迟项（必须记着，否则决议会丢）

D-01（共库）与 D-02 的结论**应当写进 `docs/registers/P0-CLOSURE.yaml`**，
但该文件在 `doc_digest` 覆盖范围内，改动会让 `traceability_gate` 变 STALE，
进而作废当前候选 `r9`。

因此本轮**只登记在验证文档与决策记录**，等下一次受控冻结窗口与批次重建一起写入。
在此之前，`p0-gate` 仍应保持 `exit 2`——**共库是技术方案选择，不等于 P0-02 关闭**：

| P0-02 关闭仍需 | 状态 |
|---|---|
| D-01 共库 | ✅ 业主已定（待写入登记） |
| D-02 实际 DDL 与实体差异清单 | ⏳ 缺生产 `SHOW CREATE TABLE` |
| D-03 `create_by` 语义 | ✅ 已定案（见 `P0-02-CREATEBY-SEMANTICS.md`） |
| 迁移脚本执行记录 / 双版本兼容 | ⏳ 未开始 |

---

## 7. 附：从源代码到底能推导出多少 DDL（能力边界）

有人会问"DDL 不能直接从代码读出来吗"。答案是**能读出一部分，且已经读出来了**，
但边界必须说清，否则会误以为生成的 DDL 等价于生产结构。

### 7.1 能推导（已实现，479 列全部覆盖）

| DDL 要素 | 来源 | 覆盖率 |
|---|---|---|
| 表名 | `@TableName` | 37/37 |
| 列名 | `@Column(name)` / `@TableId(value)` | 479 列 |
| SQL 类型 + 长度 | `@Column(type=MySqlTypeConstant.X, length=N)`；无 type 时按 Java 类型推断 | 479 列 |
| `NOT NULL` | `@Column(isNull=false)` | 22 列显式声明 |
| `AUTO_INCREMENT` | `@Column(isAutoIncrement)` / `@TableId(type=AUTO)` | 37 张主键 |
| `DEFAULT` | `@Column(defaultValue)` | 有则输出 |
| 列注释 | `@Column(comment)` | 有则输出 |
| 表注释 | `@TableComment` | 24 张表 |
| 主键 | `@Column(isKey)` / `@TableId` | 37/37 |

### 7.2 **推不出**（代码里根本没有这些声明）

| DDL 要素 | 证据 |
|---|---|
| 索引 | `@Index` / `@Unique` 出现 **0 次**（actable 支持这些注解，但项目没用） |
| 唯一约束、外键、检查约束、触发器 | 源码中无对应注解；`*.sql` 迁移文件 0 个 |
| 引擎、字符集、排序规则 | `@TableEngine` / `@TableCharset` 出现 **0 次**；只能写默认值 |
| `ON UPDATE CURRENT_TIMESTAMP`、分区、行格式 | 注解无表达能力 |
| 真实物理列顺序 | 注解顺序 ≠ 生产列序 |
| 生产实际结构是否漂移 | 静态分析无法判断 |

补充事实：actable 的自动建表配置（`mapper-locations: .../actable/mapping/...`）在
`application-local.yml:29` 是**被注释掉的**，说明运行时并未启用"注解自动建表"。
即：注解是"期望结构"，不是"已执行过的 DDL"。

### 7.3 因此生成物的定位

生成的 667 行 SQL 是 **"代码要求的结构"**，可以作为与生产比对的一方；
**不能**当作"生产已有结构"，也不能用来替代 `SHOW CREATE TABLE`。
5.1 那三类索引、以及字符集/引擎，必须来自生产库。

### 7.4 顺带发现：逻辑删除列也有两种命名

| 列名 | 表数 |
|---|---|
| `is_del` | **14** |
| `is_dtl` | **6** |

连同之前发现的 `update_by`(23) / `modify_by`(7)、`create_by` 四种长度（30/50/128/255），
这是**第三处同义不同名**。三者都属 D-01 差异清单的输入：统一即 schema 变更，
必须评估历史数据与双写兼容，不能当成"改名"顺手做。
