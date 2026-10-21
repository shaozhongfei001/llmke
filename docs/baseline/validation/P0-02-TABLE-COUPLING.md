# P0-02 / D-01：37 张表的跨服务耦合实测

日期：2026-10-22　性质：只读分析，不改源码、不改控制面
工具：`docs/baseline/validation/p0-02-table-ownership.py`
结论：**37 张表中有 9 张被多个服务直接读写**；另有 1 张表存在**两个实体定义**。

---

## 1. 为什么这件事影响 D-01

P0-02 的 D-01 是"选定共享原库或独立新库"，而设计文档 5.3 的步骤①与④互相矛盾。
裁定这件事需要先知道**耦合的实际范围**：

- 如果 37 张表各自只被一个服务读写 → 独立新库≈建表 + 迁移数据，边界清晰；
- 如果有表被多服务直接读写 → 独立新库意味着**拆共享写**，涉及事务、幂等、双写窗口，量级完全不同。

所以这里不给"该选哪个"，只给"选独立库时要拆哪些表"。

---

## 2. 实测结果

```
表=37   含表位 SQL 的 xml=27   多属主表=1   跨服务读写的表=9
```

### 2.1 跨服务读写的 9 张表

| 表 | 属主服务 | 也直接读写的服务 | 证据 |
|---|---|---|---|
| `department_info` | rag-auth-service | rag-index-service | mapper XML 表位 |
| `dept_privilege` | rag-auth-service | rag-index-service | 同上 |
| `group_privilege` | rag-auth-service | rag-index-service | 同上 |
| `user_group` | rag-auth-service | rag-index-service | 同上 |
| `user_privilege` | rag-auth-service | rag-index-service | 同上 |
| `knowledge_base` | rag-index-service | rag-auth-service | `UserPrivilegeMapper.xml:90` `FROM knowledge_base` |
| `model_info` | rag-index-service | rag-auth-service | 同上 |
| `search_config` | rag-qa-service | rag-auth-service | `UserPrivilegeMapper.xml:94` `FROM search_config` |
| `tools_database` | tools/tools-database | rag-index-service | `TLDatabaseMapper.xml:38` `FROM tools_database` |

前 5 张是"权限侧表被索引服务读"，后 4 张是"业务表被权限服务读"——**双向都有**，
说明这不是单向的"公共配置表"，而是两个服务在同一个库上互相读对方的表。

> 判定口径：只认 SQL 的**表位**（`FROM`/`JOIN`/`INTO`/`UPDATE` 之后的标识符）。
> 早先用词边界匹配时，`answer_id` 这类列名会把 `answer` 误算进 rag-auth-service —— 已修正。

### 2.2 一张表两个实体：`user_operate`

| 位置 | 映射方式 | 字段数 |
|---|---|---|
| `rag-auth-service/.../domain/model/UserOperateDO.java` | 每个字段显式 `@Column(name="…")` | 13 |
| `rag-common/.../operation/model/UserOperateDO.java` | 未写 `@Column`（依赖驼峰↔下划线默认映射） | 13 |

风险：

1. 同一张表两套映射，**任一侧改字段另一侧不会报错**，直到运行时才发现；
2. 一个显式、一个隐式 —— 隐式那侧的列名取决于 `map-underscore-to-camel-case` 配置，
   若配置被改，静默错列；
3. P0-02 的"实体模型"基线必须先决定**以哪一份为准**，否则后面的 DDL 比对会出现"两个正确答案"。

附加事实：`user_operate` 表**有** `user_id` 列（auth 版 `@Column(name="user_id")`）。
这与 P0-02 登记里"`dialogue` 只有 `create_by` 无 `user_id`"不冲突——是两张不同的表。
写差异清单时不能把这句结论外推到全库。

---

## 3. 对 D-01 的直接含义

| 若选"共享原库" | 若选"独立新库" |
|---|---|
| 9 张跨服务表保持现状，只需处理表名/连接 | 必须拆 9 张表的**写路径**（不只读路径），并定义双写/迁移窗口 |
| `user_operate` 双实体需统一，否则长期漂移 | 同上，且新库建表前必须先定"哪份实体为准" |

**新增建议（写入 D-01 待决项）**：先做"跨服务写归属"确认——本工具只能证明"服务 A 的 SQL 提到了表 B"，
不能区分读与写。`SELECT` 与 `INSERT/UPDATE` 的拆分成本差一个量级，需要按语句类型再统计一次。

---

## 4. 不判定的

| 项 | 原因 |
|---|---|
| 是否真的同一个物理库 | 需要连接串/数据源配置，本仓库不完整 |
| 读/写区分 | 本工具未按语句类型拆分（作为下一步） |
| 经 OpenFeign 的间接访问 | 那是服务调用，不是直接读写表 |
| 运行时实际访问频率 | 静态分析不覆盖 |

---

## 5. 复现

```bash
cd ~/data/dev/llmke-r8
export PATH=~/data/dev/llmke/.venv/bin:$PATH
python3 docs/baseline/validation/p0-02-table-ownership.py \
  --src ~/data/repo/RAG-SRC/_src/gien-rag/gien-rag/rag-parent --only-cross
```
