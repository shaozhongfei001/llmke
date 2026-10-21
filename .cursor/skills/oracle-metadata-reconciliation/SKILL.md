---
name: oracle_metadata_reconciliation
description: Oracle 元数据自动汇总与人工数据字典核对，以及基于核对结果的 EDWCRM 数据分析
tags: [oracle, metadata, reconciliation, edwcrm]
---

# Hermes Skill: Oracle 元数据自动汇总与人工数据字典核对

## 1. Skill 名称

`oracle_metadata_reconciliation`

---

## 2. Skill 目标

本 Skill 用于让 Hermes Agent 连接用户指定的 Oracle 数据库，自动采集数据库中的表、字段、主键、外键、索引、注释、数据类型、长度、精度、默认值、是否为空等元数据信息，并与用户提供的人工整理数据字典进行比对。

最终输出一份核对后的、可信度最高的、可用于数据治理、系统交付、数据资产盘点或数据模型确认的完整表级与字段级元数据清单。

---

## 3. 适用场景

本 Skill 适用于以下场景：

1. 数据治理中的元数据盘点。
2. 数据仓库、数据湖、数据中台建设前的数据资产梳理。
3. Oracle 数据库表结构与人工数据字典的一致性核查。
4. 数据库改造、系统迁移、国产化替代前的数据模型确认。
5. 数据标准落地过程中的字段命名、类型、注释、主外键关系核查。
6. 生成标准化数据字典、元数据清单、表结构说明书。
7. 对人工维护的数据字典进行自动校验和修正建议输出。

---

## 4. 输入要求

### 4.1 必需输入

用户必须提供以下信息：

#### 4.1.1 Oracle 数据库连接信息

支持 `service_name` 方式：

```yaml
oracle_connection:
  host: "<主机名或IP>"
  port: 1521
  service_name: "<service_name>"
  username: "<用户名>"
  password: "<密码——建议用环境变量引用>"
  schema: "<目标Schema>"
```

也支持 `sid` 方式：

```yaml
oracle_connection:
  host: "<Oracle数据库地址>"
  port: 1521
  sid: "<SID>"
  username: "<用户名>"
  password: "<密码或密钥引用>"
  schema: "<目标Schema>"
```

#### 4.1.2 人工数据字典文件

支持以下格式：

```yaml
dictionary_file:
  path: "<人工数据字典目录>"
  format: "xlsx | csv | json | markdown"
  description: "<按优先级列出字典文件：最可靠的基础表字典 / 汇总层模型字典 / 字段级分析字典>"
```

推荐使用 Excel 格式。

---

### 4.2 人工数据字典推荐字段

人工数据字典建议包含以下字段：

| 字段名 | 含义 | 是否必需 |
|---|---|---|
| table_name | 表名 | 是 |
| table_comment | 表中文名或表说明 | 否 |
| column_name | 字段名 | 是 |
| column_comment | 字段中文名或字段说明 | 否 |
| data_type | 数据类型 | 否 |
| data_length | 字段长度 | 否 |
| data_precision | 数值精度 | 否 |
| data_scale | 小数位数 | 否 |
| nullable | 是否允许为空 | 否 |
| primary_key | 是否主键 | 否 |
| default_value | 默认值 | 否 |
| business_meaning | 业务含义 | 否 |
| value_range | 取值范围 | 否 |
| standard_code | 数据标准编码 | 否 |
| source_system | 来源系统 | 否 |
| owner | 责任人 | 否 |

---

## 5. 输出结果

Skill 最终应输出以下内容：

```yaml
outputs:
  reconciled_metadata:
    description: "核对后的最终元数据清单"
    format: "xlsx | csv | json | markdown"

  comparison_report:
    description: "Oracle元数据与人工数据字典的差异报告"
    format: "xlsx | markdown"

  issue_summary:
    description: "问题汇总，包括缺失字段、类型不一致、注释冲突、主键差异等"
    format: "markdown"

  confidence_report:
    description: "每个表、字段的最终采信来源与置信度说明"
    format: "xlsx | markdown"
```

---

## 6. 核心能力

Hermes Agent 执行本 Skill 时，应具备以下能力：

1. 连接 Oracle 数据库。
2. 自动读取 Oracle 系统视图中的元数据。
3. 自动解析用户提供的人工数据字典。
4. 标准化 Oracle 元数据和人工数据字典字段。
5. 对表级信息进行比对。
6. 对字段级信息进行比对。
7. 判断冲突信息的可信来源。
8. 输出最终核准后的元数据。
9. 输出详细差异报告。
10. 输出问题清单和修复建议。
11. 对敏感字段进行识别与标记。
12. 对每项元数据生成最终采信来源与置信度。

---

## 7. 执行流程

### Step 1: 校验输入参数

Agent 应首先检查以下内容：

1. Oracle 连接信息是否完整。
2. 是否指定了 `schema`。
3. 人工数据字典文件是否存在。
4. 人工数据字典格式是否可解析。
5. 输出路径是否可写。
6. 当前执行环境是否具备 Oracle 客户端或驱动依赖。
7. 是否具备读取 Oracle 系统视图的权限。

如果缺少必要信息，应向用户明确指出缺失项，不得继续盲目执行。

---

### Step 2: 连接 Oracle 数据库

Agent 使用用户提供的连接信息连接 Oracle。

连接时应遵循以下要求：

1. 不在日志中明文打印密码。
2. 连接失败时返回明确错误原因。
3. 优先使用只读账号。
4. 连接成功后验证目标 Schema 是否存在。
5. 不执行任何 DDL 或 DML 操作。

示例连接逻辑：

```python
import oracledb

dsn = oracledb.makedsn(
    host=host,
    port=port,
    service_name=service_name
)

connection = oracledb.connect(
    user=username,
    password=password,
    dsn=dsn
)
```

如果使用 SID：

```python
import oracledb

dsn = oracledb.makedsn(
    host=host,
    port=port,
    sid=sid
)

connection = oracledb.connect(
    user=username,
    password=password,
    dsn=dsn
)
```

---

### Step 3: 采集 Oracle 表级元数据

Agent 应从 Oracle 系统视图中采集表级信息。

推荐查询视图：

```sql
ALL_TABLES
ALL_TAB_COMMENTS
ALL_OBJECTS
ALL_USERS
```

推荐采集字段：

| 元数据项 | Oracle 来源 |
|---|---|
| schema_name | ALL_TABLES.OWNER |
| table_name | ALL_TABLES.TABLE_NAME |
| table_comment | ALL_TAB_COMMENTS.COMMENTS |
| table_type | ALL_OBJECTS.OBJECT_TYPE |
| tablespace_name | ALL_TABLES.TABLESPACE_NAME |
| num_rows | ALL_TABLES.NUM_ROWS |
| last_analyzed | ALL_TABLES.LAST_ANALYZED |
| created_time | ALL_OBJECTS.CREATED |
| last_ddl_time | ALL_OBJECTS.LAST_DDL_TIME |

示例 SQL：

```sql
SELECT
    t.owner AS schema_name,
    t.table_name,
    c.comments AS table_comment,
    t.tablespace_name,
    t.num_rows,
    t.last_analyzed,
    o.created AS created_time,
    o.last_ddl_time
FROM all_tables t
LEFT JOIN all_tab_comments c
    ON t.owner = c.owner
   AND t.table_name = c.table_name
LEFT JOIN all_objects o
    ON t.owner = o.owner
   AND t.table_name = o.object_name
   AND o.object_type = 'TABLE'
WHERE t.owner = :schema_name
ORDER BY t.table_name
```

---

### Step 4: 采集 Oracle 字段级元数据

Agent 应从 Oracle 系统视图中采集字段级信息。

推荐查询视图：

```sql
ALL_TAB_COLUMNS
ALL_COL_COMMENTS
```

推荐采集字段：

| 元数据项 | Oracle 来源 |
|---|---|
| schema_name | ALL_TAB_COLUMNS.OWNER |
| table_name | ALL_TAB_COLUMNS.TABLE_NAME |
| column_name | ALL_TAB_COLUMNS.COLUMN_NAME |
| column_id | ALL_TAB_COLUMNS.COLUMN_ID |
| data_type | ALL_TAB_COLUMNS.DATA_TYPE |
| data_length | ALL_TAB_COLUMNS.DATA_LENGTH |
| data_precision | ALL_TAB_COLUMNS.DATA_PRECISION |
| data_scale | ALL_TAB_COLUMNS.DATA_SCALE |
| nullable | ALL_TAB_COLUMNS.NULLABLE |
| default_value | ALL_TAB_COLUMNS.DATA_DEFAULT |
| column_comment | ALL_COL_COMMENTS.COMMENTS |

示例 SQL：

```sql
SELECT
    c.owner AS schema_name,
    c.table_name,
    c.column_name,
    c.column_id,
    c.data_type,
    c.data_length,
    c.data_precision,
    c.data_scale,
    c.nullable,
    c.data_default AS default_value,
    cc.comments AS column_comment
FROM all_tab_columns c
LEFT JOIN all_col_comments cc
    ON c.owner = cc.owner
   AND c.table_name = cc.table_name
   AND c.column_name = cc.column_name
WHERE c.owner = :schema_name
ORDER BY c.table_name, c.column_id
```

---

### Step 5: 采集主键信息

Agent 应识别每张表的主键字段。

推荐查询视图：

```sql
ALL_CONSTRAINTS
ALL_CONS_COLUMNS
```

示例 SQL：

```sql
SELECT
    acc.owner AS schema_name,
    acc.table_name,
    acc.column_name,
    acc.position,
    ac.constraint_name
FROM all_constraints ac
JOIN all_cons_columns acc
    ON ac.owner = acc.owner
   AND ac.constraint_name = acc.constraint_name
WHERE ac.owner = :schema_name
  AND ac.constraint_type = 'P'
ORDER BY acc.table_name, acc.position
```

---

### Step 6: 采集外键信息

Agent 应识别外键关系，包括源表、源字段、目标表、目标字段。

示例 SQL：

```sql
SELECT
    fk.owner AS schema_name,
    fk.table_name AS child_table,
    fkc.column_name AS child_column,
    pk.table_name AS parent_table,
    pkc.column_name AS parent_column,
    fk.constraint_name AS fk_constraint_name,
    pk.constraint_name AS pk_constraint_name
FROM all_constraints fk
JOIN all_cons_columns fkc
    ON fk.owner = fkc.owner
   AND fk.constraint_name = fkc.constraint_name
JOIN all_constraints pk
    ON fk.r_owner = pk.owner
   AND fk.r_constraint_name = pk.constraint_name
JOIN all_cons_columns pkc
    ON pk.owner = pkc.owner
   AND pk.constraint_name = pkc.constraint_name
   AND fkc.position = pkc.position
WHERE fk.owner = :schema_name
  AND fk.constraint_type = 'R'
ORDER BY fk.table_name, fkc.position
```

---

### Step 7: 采集索引信息

Agent 应采集普通索引、唯一索引及索引字段顺序。

推荐查询视图：

```sql
ALL_INDEXES
ALL_IND_COLUMNS
```

示例 SQL：

```sql
SELECT
    i.owner AS schema_name,
    i.table_name,
    i.index_name,
    i.uniqueness,
    ic.column_name,
    ic.column_position
FROM all_indexes i
JOIN all_ind_columns ic
    ON i.owner = ic.index_owner
   AND i.index_name = ic.index_name
WHERE i.owner = :schema_name
ORDER BY i.table_name, i.index_name, ic.column_position
```

---

### Step 8: 读取并标准化人工数据字典

Agent 应读取用户提供的数据字典，并进行字段标准化。

#### 标准化规则

1. 表名统一转为大写。
2. 字段名统一转为大写。
3. 去除前后空格。
4. 将中文括号、全角符号转换为半角符号。
5. 将 `是/否`、`Y/N`、`YES/NO`、`true/false` 统一为标准布尔值。
6. 将数据类型统一转换为 Oracle 风格。
7. 空字符串、`N/A`、`无`、`-` 统一视为空值。
8. 日期、数字、布尔字段应转换为可比对的标准格式。
9. Excel 中合并单元格导致的空表名，应根据上下文自动向下填充。

#### 数据类型标准化示例

| 原始类型 | 标准类型 |
|---|---|
| VARCHAR | VARCHAR2 |
| VARCHAR2 | VARCHAR2 |
| NUMBER(10,0) | NUMBER |
| NUMERIC | NUMBER |
| INTEGER | NUMBER |
| INT | NUMBER |
| DATE | DATE |
| DATETIME | DATE |
| TIMESTAMP | TIMESTAMP |
| CHAR | CHAR |
| CLOB | CLOB |
| BLOB | BLOB |

---

### Step 9: 构建 Oracle 元数据基准表

Agent 应将采集到的 Oracle 元数据整合为统一结构。

最终 Oracle 元数据结构如下：

```yaml
oracle_metadata_record:
  schema_name: string
  table_name: string
  table_comment: string
  column_name: string
  column_comment: string
  column_id: integer
  data_type: string
  data_length: integer
  data_precision: integer
  data_scale: integer
  nullable: string
  default_value: string
  is_primary_key: boolean
  primary_key_position: integer
  is_foreign_key: boolean
  referenced_table: string
  referenced_column: string
  indexes:
    - index_name: string
      uniqueness: string
      column_position: integer
```

---

### Step 10: 表级比对

Agent 应对 Oracle 表清单与人工数据字典中的表清单进行比对。

#### 表级比对项

| 比对项 | 说明 |
|---|---|
| 表是否存在于 Oracle | 人工字典有，Oracle 无 |
| 表是否存在于人工字典 | Oracle 有，人工字典无 |
| 表注释是否一致 | 比较 Oracle 表注释和人工表说明 |
| 表命名是否一致 | 检查大小写、别名、命名规范 |
| 表记录数是否异常 | 基于 Oracle num_rows 辅助判断是否废弃 |

#### 表级差异类型

```yaml
table_diff_types:
  - ONLY_IN_ORACLE
  - ONLY_IN_DICTIONARY
  - TABLE_COMMENT_MISMATCH
  - TABLE_NAME_CASE_MISMATCH
  - POSSIBLE_DEPRECATED_TABLE
```

---

### Step 11: 字段级比对

Agent 应按 `table_name + column_name` 对字段进行比对。

#### 字段级比对项

| 比对项 | 说明 |
|---|---|
| 字段是否存在 | Oracle 有而字典无，或字典有而 Oracle 无 |
| 字段类型是否一致 | 比较 data_type |
| 字段长度是否一致 | 比较 data_length |
| 字段精度是否一致 | 比较 data_precision |
| 小数位是否一致 | 比较 data_scale |
| 是否允许为空是否一致 | 比较 nullable |
| 默认值是否一致 | 比较 default_value |
| 字段注释是否一致 | 比较 column_comment |
| 主键标识是否一致 | 比较 primary_key |
| 字段顺序是否一致 | 比较 column_id 或人工排序 |

#### 字段级差异类型

```yaml
column_diff_types:
  - ONLY_IN_ORACLE
  - ONLY_IN_DICTIONARY
  - DATA_TYPE_MISMATCH
  - DATA_LENGTH_MISMATCH
  - DATA_PRECISION_MISMATCH
  - DATA_SCALE_MISMATCH
  - NULLABLE_MISMATCH
  - DEFAULT_VALUE_MISMATCH
  - COLUMN_COMMENT_MISMATCH
  - PRIMARY_KEY_MISMATCH
  - COLUMN_ORDER_MISMATCH
```

---

## 8. 信息采信规则

当 Oracle 元数据与人工数据字典不一致时，Agent 应根据以下规则决定最终采信结果。

---

### 8.1 结构性信息优先采信 Oracle

以下字段原则上以 Oracle 当前结构为准：

```yaml
oracle_authoritative_fields:
  - table_name
  - column_name
  - data_type
  - data_length
  - data_precision
  - data_scale
  - nullable
  - default_value
  - primary_key
  - foreign_key
  - index
  - column_order
```

原因：这些信息代表数据库真实运行结构。

---

### 8.2 业务语义信息优先采信人工数据字典

以下字段原则上优先采信人工数据字典：

```yaml
dictionary_authoritative_fields:
  - table_comment
  - column_comment
  - business_meaning
  - value_range
  - standard_code
  - source_system
  - owner
```

前提是人工字典内容非空且具有明确业务含义。

---

### 8.3 Oracle 注释与人工注释冲突时的处理

当 Oracle 注释与人工数据字典注释不一致时，Agent 应按以下规则判断：

1. 如果人工注释为空，使用 Oracle 注释。
2. 如果 Oracle 注释为空，使用人工注释。
3. 如果两者语义基本一致，仅表达不同，优先使用人工注释，并标记为 `SEMANTICALLY_EQUIVALENT`。
4. 如果两者明显冲突，优先保留人工注释作为最终业务描述，同时在差异报告中标记为 `COMMENT_CONFLICT`。
5. 如果人工注释明显是占位符，例如 `待补充`、`无`、`-`、`N/A`，则使用 Oracle 注释。

---

### 8.4 字段类型冲突时的处理

字段类型、长度、精度、小数位冲突时，最终结果必须以 Oracle 为准。

示例：

```yaml
oracle:
  column_name: AMOUNT
  data_type: NUMBER
  data_precision: 18
  data_scale: 2

dictionary:
  column_name: AMOUNT
  data_type: VARCHAR2
  data_length: 100

final:
  column_name: AMOUNT
  data_type: NUMBER
  data_precision: 18
  data_scale: 2
  source_of_truth: ORACLE
  issue_type: DATA_TYPE_MISMATCH
```

---

### 8.5 字段存在性冲突时的处理

#### Oracle 有，人工字典无

判断为数据库真实存在字段，应纳入最终结果，并标记：

```yaml
status: ONLY_IN_ORACLE
action: ADD_TO_FINAL_METADATA
recommendation: "建议补充人工数据字典"
```

#### 人工字典有，Oracle 无

不应直接纳入最终结构性元数据，应标记为疑似历史字段、设计字段或已删除字段：

```yaml
status: ONLY_IN_DICTIONARY
action: EXCLUDE_FROM_FINAL_METADATA_BY_DEFAULT
recommendation: "请确认该字段是否已删除、尚未上线或属于其他Schema"
```

除非用户明确要求保留设计字段，否则最终元数据不应包含 Oracle 中不存在的字段。

---

## 9. 置信度评分规则

Agent 应为每个最终元数据字段生成置信度评分。

### 9.1 评分范围

```yaml
confidence_score:
  min: 0.0
  max: 1.0
```

### 9.2 推荐评分规则

| 场景 | 置信度 |
|---|---:|
| Oracle 与人工字典完全一致 | 1.00 |
| Oracle 有结构信息，人工字典无 | 0.90 |
| Oracle 结构信息与人工字典冲突，但采信 Oracle | 0.85 |
| Oracle 注释为空，采信人工注释 | 0.80 |
| Oracle 注释与人工注释语义接近 | 0.85 |
| Oracle 注释与人工注释明显冲突 | 0.60 |
| 人工字典有，Oracle 无 | 0.30 |
| 字段名疑似匹配但无法确定 | 0.40 |

---

## 10. 输出字段规范

最终输出的核准元数据应包含以下字段：

| 字段名 | 说明 |
|---|---|
| schema_name | Schema 名称 |
| table_name | 表名 |
| final_table_comment | 最终表说明 |
| column_name | 字段名 |
| column_id | 字段顺序 |
| final_column_comment | 最终字段说明 |
| data_type | 数据类型 |
| data_length | 字段长度 |
| data_precision | 数值精度 |
| data_scale | 小数位数 |
| nullable | 是否允许为空 |
| default_value | 默认值 |
| is_primary_key | 是否主键 |
| primary_key_position | 主键顺序 |
| is_foreign_key | 是否外键 |
| referenced_table | 引用表 |
| referenced_column | 引用字段 |
| index_names | 所属索引 |
| business_meaning | 业务含义 |
| value_range | 取值范围 |
| standard_code | 数据标准编码 |
| source_system | 来源系统 |
| owner | 责任人 |
| final_source | 最终采信来源 |
| diff_status | 差异状态 |
| confidence_score | 置信度 |
| recommendation | 处理建议 |
| sensitive_flag | 是否敏感字段 |
| sensitive_type | 敏感字段类型 |

---

## 11. 差异报告规范

差异报告应至少包含以下 Sheet 或章节：

```yaml
comparison_report:
  sheets:
    - summary
    - table_differences
    - column_differences
    - type_differences
    - comment_differences
    - primary_key_differences
    - only_in_oracle
    - only_in_dictionary
    - sensitive_fields
    - final_metadata
```

---

### 11.1 Summary

汇总整体核对结果。

| 指标 | 说明 |
|---|---|
| oracle_table_count | Oracle 表数量 |
| dictionary_table_count | 人工字典表数量 |
| final_table_count | 最终采信表数量 |
| oracle_column_count | Oracle 字段数量 |
| dictionary_column_count | 人工字典字段数量 |
| final_column_count | 最终采信字段数量 |
| matched_column_count | 完全匹配字段数量 |
| mismatch_column_count | 存在差异字段数量 |
| only_in_oracle_count | 仅 Oracle 存在字段数量 |
| only_in_dictionary_count | 仅人工字典存在字段数量 |
| sensitive_field_count | 识别出的敏感字段数量 |

---

### 11.2 Table Differences

表级差异报告字段：

| 字段名 | 说明 |
|---|---|
| table_name | 表名 |
| diff_type | 差异类型 |
| oracle_value | Oracle 值 |
| dictionary_value | 人工字典值 |
| final_value | 最终采信值 |
| confidence_score | 置信度 |
| recommendation | 处理建议 |

---

### 11.3 Column Differences

字段级差异报告字段：

| 字段名 | 说明 |
|---|---|
| table_name | 表名 |
| column_name | 字段名 |
| diff_type | 差异类型 |
| oracle_value | Oracle 值 |
| dictionary_value | 人工字典值 |
| final_value | 最终采信值 |
| final_source | 最终采信来源 |
| confidence_score | 置信度 |
| recommendation | 处理建议 |

---

## 12. 异常处理

### 12.1 数据库连接失败

返回：

```yaml
error_type: ORACLE_CONNECTION_FAILED
message: "无法连接 Oracle 数据库，请检查 host、port、service_name、username、password、网络和权限。"
```

---

### 12.2 Schema 不存在

返回：

```yaml
error_type: SCHEMA_NOT_FOUND
message: "指定 Schema 不存在或当前账号无权访问。"
```

---

### 12.3 数据字典无法解析

返回：

```yaml
error_type: DICTIONARY_PARSE_FAILED
message: "人工数据字典文件无法解析，请检查文件格式、Sheet名称和字段列名。"
```

---

### 12.4 数据字典缺少关键字段

返回：

```yaml
error_type: DICTIONARY_REQUIRED_COLUMNS_MISSING
message: "人工数据字典缺少 table_name 或 column_name 字段，无法进行字段级比对。"
```

---

### 12.5 权限不足

返回：

```yaml
error_type: ORACLE_PERMISSION_DENIED
message: "当前账号无法访问 Oracle 系统视图或目标 Schema，请确认是否具备 ALL_TABLES、ALL_TAB_COLUMNS 等视图访问权限。"
```

---

## 13. 安全要求

Agent 执行本 Skill 时必须遵循以下安全规则：

1. 不得在日志、报告、异常信息中输出数据库密码。
2. 默认只执行只读 SQL。
3. 禁止执行 DDL、DML、DROP、TRUNCATE、DELETE、UPDATE、INSERT 等变更语句。
4. 禁止扫描用户未授权的 Schema。
5. 输出报告中不得包含敏感连接信息。
6. 对包含敏感字段名称的字段，如身份证号、手机号、银行卡号、密码、密钥等，应在报告中标记敏感字段风险。
7. 若用户要求修改数据库结构，应拒绝在本 Skill 中执行，并提示该 Skill 仅用于元数据读取与核对。
8. 连接字符串、用户名、Schema 可记录，但密码、Token、密钥不得明文记录。
9. 对异常堆栈进行脱敏处理后再输出。

---

## 14. 敏感字段识别规则

Agent 应对字段名和字段注释进行敏感信息识别。

推荐关键词：

```yaml
sensitive_keywords:
  personal_identity:
    - ID_CARD
    - IDCARD
    - CERT_NO
    - CERTIFICATE_NO
    - 身份证
    - 证件号

  phone:
    - PHONE
    - MOBILE
    - TEL
    - 手机号
    - 电话

  bank:
    - BANK_CARD
    - CARD_NO
    - ACCOUNT_NO
    - 银行卡
    - 账号

  password:
    - PASSWORD
    - PASSWD
    - PWD
    - 密码
    - 口令

  address:
    - ADDRESS
    - ADDR
    - 地址

  email:
    - EMAIL
    - MAIL
    - 邮箱
```

识别后应输出：

```yaml
sensitive_flag: true
sensitive_type: "phone | id_card | bank_card | password | address | email | unknown"
```

---

## 15. 推荐实现伪代码

```python
def run_skill(config):
    validate_config(config)

    oracle_conn = connect_oracle(config.oracle_connection)

    oracle_tables = fetch_oracle_tables(oracle_conn, config.schema)
    oracle_columns = fetch_oracle_columns(oracle_conn, config.schema)
    oracle_primary_keys = fetch_oracle_primary_keys(oracle_conn, config.schema)
    oracle_foreign_keys = fetch_oracle_foreign_keys(oracle_conn, config.schema)
    oracle_indexes = fetch_oracle_indexes(oracle_conn, config.schema)

    oracle_metadata = build_oracle_metadata(
        tables=oracle_tables,
        columns=oracle_columns,
        primary_keys=oracle_primary_keys,
        foreign_keys=oracle_foreign_keys,
        indexes=oracle_indexes
    )

    dictionary_metadata = load_dictionary(config.dictionary_file)
    dictionary_metadata = normalize_dictionary(dictionary_metadata)

    comparison_result = compare_metadata(
        oracle_metadata=oracle_metadata,
        dictionary_metadata=dictionary_metadata
    )

    final_metadata = reconcile_metadata(
        comparison_result=comparison_result,
        rules=config.reconciliation_rules
    )

    final_metadata = detect_sensitive_fields(final_metadata)

    reports = generate_reports(
        final_metadata=final_metadata,
        comparison_result=comparison_result
    )

    return reports
```

---

## 16. 核心比对逻辑

### 16.1 表匹配 Key

```python
table_key = normalize(table_name)
```

### 16.2 字段匹配 Key

```python
column_key = normalize(table_name) + "." + normalize(column_name)
```

### 16.3 标准化函数

```python
def normalize_name(value):
    if value is None:
        return None
    return str(value).strip().upper()
```

### 16.4 空值判断

```python
EMPTY_VALUES = ["", " ", "-", "N/A", "NA", "无", "暂无", "待补充", None]

def is_empty(value):
    return value is None or str(value).strip().upper() in EMPTY_VALUES
```

---

## 17. 最终采信逻辑

```python
def reconcile_field(oracle_field, dictionary_field):
    final = {}

    if oracle_field and dictionary_field:
        final["table_name"] = oracle_field["table_name"]
        final["column_name"] = oracle_field["column_name"]

        # 结构性信息采信 Oracle
        for key in [
            "data_type",
            "data_length",
            "data_precision",
            "data_scale",
            "nullable",
            "default_value",
            "is_primary_key",
            "is_foreign_key",
            "referenced_table",
            "referenced_column"
        ]:
            final[key] = oracle_field.get(key)

        # 业务语义优先采信人工数据字典
        for key in [
            "column_comment",
            "business_meaning",
            "value_range",
            "standard_code",
            "source_system",
            "owner"
        ]:
            if not is_empty(dictionary_field.get(key)):
                final[key] = dictionary_field.get(key)
            else:
                final[key] = oracle_field.get(key)

        final["diff_status"] = calculate_diff_status(oracle_field, dictionary_field)
        final["confidence_score"] = calculate_confidence(oracle_field, dictionary_field)

    elif oracle_field and not dictionary_field:
        final = oracle_field
        final["diff_status"] = "ONLY_IN_ORACLE"
        final["confidence_score"] = 0.90
        final["recommendation"] = "建议补充人工数据字典"

    elif dictionary_field and not oracle_field:
        final = dictionary_field
        final["diff_status"] = "ONLY_IN_DICTIONARY"
        final["confidence_score"] = 0.30
        final["recommendation"] = "Oracle中不存在该字段，建议确认是否为历史字段、设计字段或错误字段"
        final["exclude_from_final"] = True

    return final
```

---

## 18. 输出文件命名规范

默认输出文件命名：

```yaml
output_files:
  final_metadata: "final_reconciled_metadata_<schema>_<yyyymmddhhmmss>.xlsx"
  comparison_report: "metadata_comparison_report_<schema>_<yyyymmddhhmmss>.xlsx"
  issue_summary: "metadata_issue_summary_<schema>_<yyyymmddhhmmss>.md"
  confidence_report: "metadata_confidence_report_<schema>_<yyyymmddhhmmss>.xlsx"
```

---

## 19. 成功完成标准

Skill 执行完成后，必须满足以下标准：

1. 成功连接 Oracle 并读取目标 Schema 的元数据。
2. 成功解析人工数据字典。
3. 输出 Oracle 元数据与人工数据字典的差异结果。
4. 输出最终核准元数据。
5. 每个字段均有明确的最终采信来源。
6. 每个字段均有置信度评分。
7. 所有仅存在于 Oracle 或仅存在于人工字典的对象均被标记。
8. 不泄露数据库密码或敏感连接信息。
9. 不执行任何数据库变更操作。
10. 输出内容可供业务人员、数据治理人员和开发人员共同查看。

---

## 20. Agent 行为要求

Hermes Agent 执行本 Skill 时，应遵循以下行为要求：

1. 如果输入不完整，应先指出缺失项，不得盲目执行。
2. 如果 Oracle 与人工数据字典存在冲突，应明确说明冲突来源。
3. 不应简单地认为人工数据字典一定正确。
4. 不应简单地认为 Oracle 注释一定正确。
5. 结构性信息以 Oracle 当前数据库为准。
6. 业务语义信息优先参考人工数据字典。
7. 对无法判断的冲突，应保留问题标记并给出人工确认建议。
8. 输出结果应具备可审计性。
9. 输出报告应适合业务人员、数据治理人员和开发人员共同查看。
10. 对高风险差异，例如字段缺失、主键变化、字段类型变化，应在报告中突出显示。
11. 对人工字典中存在但 Oracle 中不存在的字段，不应默认纳入最终正式元数据。
12. 对 Oracle 中存在但人工字典中缺失的字段，应默认纳入最终元数据，并建议补充人工字典。

---

## 21. 示例最终输出记录

```yaml
schema_name: ACRM
table_name: CUSTOMER_INFO
final_table_comment: 客户基本信息表
column_name: CUSTOMER_ID
column_id: 1
final_column_comment: 客户唯一标识
data_type: VARCHAR2
data_length: 64
data_precision: null
data_scale: null
nullable: N
default_value: null
is_primary_key: true
primary_key_position: 1
is_foreign_key: false
referenced_table: null
referenced_column: null
index_names:
  - PK_CUSTOMER_INFO
business_meaning: 客户在CRM系统中的唯一编号
value_range: null
standard_code: CUST_ID
source_system: CRM
owner: 客户域数据负责人
final_source: ORACLE_STRUCTURE_AND_DICTIONARY_BUSINESS
diff_status: MATCHED
confidence_score: 1.0
recommendation: 无需处理
sensitive_flag: false
sensitive_type: null
```

---

## 22. 推荐配置模板

```yaml
skill_name: oracle_metadata_reconciliation

oracle_connection:
  host: "<主机名或IP>"
  port: 1521
  service_name: "<service_name>"
  username: "<用户名>"
  password: "<密码——建议用环境变量引用>"
  schema: "<目标Schema>"

dictionary_file:
  path: "<人工数据字典目录>"
  format: "xlsx"
  description: "<按优先级列出字典文件>"
  sheet_name: "*"

output:
  path: "<输出目录>"
  formats:
    - xlsx
    - markdown

reconciliation_rules:
  structural_source_of_truth: "ORACLE"
  business_source_of_truth: "DICTIONARY"
  include_only_in_oracle: true
  include_only_in_dictionary: false
  detect_sensitive_fields: true
  generate_confidence_score: true

logging:
  level: "INFO"
  mask_sensitive_info: true
```

---

## 23. EDWCRM Schema 领域知识参考

本 Skill 包含 EDWCRM Schema 的领域知识参考文件，供元数据核对和数据查询分析时使用：

- `references/edwcrm_schema_notes.md` — EDWCRM Schema 表关系、贷款产品类型编码 (YWPZ)、逾期率口径、关键查询模板、SQL 陷阱
- `references/known_pitfalls.md` — 已知陷阱（字符集、Excel 解析、Oracle 连接、Python 作用域等）

当用户基于已核对的元数据进行 Oracle 数据分析（如贷款余额、逾期率统计）时，应查阅 `edwcrm_schema_notes.md` 获取表关系和字段语义信息，避免重复探索。

---

## 24. 非目标范围

本 Skill 不负责以下事项：

1. 修改 Oracle 表结构。
2. 自动更新 Oracle 注释。
3. 自动写回人工数据字典。
4. 执行数据质量探查。
5. 抽取业务数据内容。
6. 扫描用户未授权的 Schema。
7. 生成物理建模 DDL。
8. 执行数据库迁移。
9. 自动判定业务口径正确性。
10. 自动删除或修改人工数据字典中的历史字段。

如需上述能力，应设计独立 Skill。

---

## 24. 最终说明

本 Skill 的核心原则是：

1. Oracle 当前数据库结构代表实际运行状态。
2. 人工数据字典代表业务语义和管理口径。
3. 结构性冲突优先采信 Oracle。
4. 业务语义冲突优先参考人工数据字典，但必须保留差异标记。
5. 最终输出必须可追溯、可审计、可人工复核。
