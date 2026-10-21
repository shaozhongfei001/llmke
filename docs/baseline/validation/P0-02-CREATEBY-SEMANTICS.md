# P0-02 / D-03：`create_by` 到底存什么（源码证据链）

日期：2026-10-22　性质：只读分析，不改源码、不改控制面
结论：**`create_by` 存的是登录账号 `user_name`（字符串），既不是用户 ID，也不是姓名。**

---

## 1. 为什么这条必须先定

P0-02 的 D-03 原文是"确认 `create_by` 语义（用户 ID / 账号 / 姓名），不得机械替换 `user_id`"。
如果按"用户 ID"建表和迁移，所有按创建人过滤的查询都会返回空集，而且**不会报错**——
是典型的静默错误。所以必须有代码级证据，而不是靠命名猜测。

---

## 2. 证据链（五个独立来源，结论一致）

### ① 实体注解：注释写"创建人"，类型是 String

```java
@Column(name = "create_by", comment = "创建人", length = 50)
private String createBy;
```
摘自 `DialogueDO.java:44`；同类定义出现在 **30 张表**的 DO 中。

### ② 自动填充：取的是 `getUserName()`

```java
// rag-common/.../CustomMetaObjectHandler.java
public void insertFill(MetaObject metaObject) {
    this.strictInsertFill(metaObject, "createBy", String.class, getCurrentUser());
    ...
}
private String getCurrentUser() {
    return UserContext.getUser().getUserName();     // ← 账号
}
```
注：同一个 handler 还填 `updateBy`、`gmtCreate`、`gmtModified`；`updateFill` 只更新 `updateBy`/`gmtModified`。

### ③ 仓储实现：显式 `setCreateBy(userName)`

| 位置 | 代码 |
|---|---|
| `DialogueRepositoryImpl:39` | `dialogue.setCreateBy(userName);` |
| `FeedbackRepositoryImpl:52` | `feedback.setCreateBy(userName);` |
| `ApiKeyInfoRepositoryImpl:44` | `apiKeyInfo.setCreateBy(userName);` |
| `SearchConfigRepositoryImpl:72` | `config.setCreateBy(userName);` |
| `UserInfoRepositoryImpl:82` | `userInfoDO.setCreateBy(userInfo.getUserName());` |
| `RoleResourceRepositoryImpl:41` 等 8 处 | `xxx.setCreateBy(userName);` |

**没有一处**是 `setCreateBy(userId)` 或 `setCreateBy(String.valueOf(id))`。

### ④ Mapper XML：`create_by=#{userName}`

```xml
<!-- rag-qa-service/.../SearchConfigMapper.xml:128 -->
create_by=#{userName}, modify_by=#{userName}
```
参数名就是 `userName`，不是 `userId`。

### ⑤ 查询侧：按 `userName` 等值比较

| 位置 | 代码 |
|---|---|
| `DialogueRepositoryImpl:165` | `.eq(DialogueDO::getCreateBy, userName)` |
| `TLDatabaseRepositoryImpl:67/69/96` | `.eq(...getCreateBy, userName)` / `.ne(..., userName)` / `.ne(..., UserContext.getUser().getUserName())` |
| `ModelInfoRepositoryImpl:73/95` | `.eq(..., ModelInfoDO::getCreateBy, param.getCreateBy())` |
| `UserPrivilegeRepositoryImpl:171` | `.eq(..., getCreateBy, queryParam.getCreateBy())` |

**没有任何一处**把它与数值 ID 比较。

### ⑥ 反向印证：`user_info` 表里没有 `user_id` 列

在 `UserInfoDO.java` 中 `@Column(name = "user_id")` 命中数为 **0**；
用户表以 `id` 为主键，`user_name`（注释"用户名"，`length = 128`，`isNull = false`）才是账号。
这直接印证 P0-02 登记里那条"`dialogue` 共 13 字段且只有 `create_by`，无 `user_id`"。

---

## 3. 例外情况（不影响结论，但迁移时必须处理）

| 场景 | 位置 | 含义 |
|---|---|---|
| 复制旧值 | `TLTableRepositoryImpl:98`、`TLTableColumnRepositoryImpl:88`、`TLTableFileRepositoryImpl:94` | 更新时 `setCreateBy(old.getCreateBy())`，即**不覆盖原始创建人** |
| 透传 | `DepartmentInfoConvertor:75` | `setCreateBy(DO.getCreateBy())`，DO→实体原样带过 |

迁移脚本若用"当前操作人"回填历史数据的 `create_by`，会破坏这三处的语义（把创建人改成迁移人）。

---

## 4. 迁移风险（同名列不同口径，这才是 "DDL 原样复用" 的坑）

| 维度 | 实测 |
|---|---|
| 有 `create_by` 的表 | **30 / 37** |
| `create_by` 长度分布 | `30`×6 表、`50`×19 表、`128`×4 表、**`255`×1 表**（`DepartmentInfoDO`） |
| 更新人列名 | `update_by` **23 表** vs `modify_by` **7 表**（无表同时含两个） |

含义：

1. **同名不同宽**：按最宽 255 建表不会截断，但按 30 建就会截断 50/128/255 表的写入；
   反过来，各服务按自己 DAO 的 `length` 校验，跨表 JOIN 或统一治理时会不一致。
2. **同义不同名**：`update_by` / `modify_by` 分裂在 7 张表上；
   P0-02 若要求"统一改为 `updated_by`"，就**不是原样复用**，属于 schema 变更，需要迁移脚本与回滚方案。
3. `create_by` 缺失的 7 张表需要单独确认：是确实没有创建人概念，还是漏建。

以上三条都应作为 D-01（差异清单）的输入，而不是"看起来一样就照抄"。

---

## 5. 结论与仍需人工裁定的部分

### 已有代码级答案

| 问题 | 答案 | 证据 |
|---|---|---|
| `create_by` 是用户 ID？ | **否** | 五处写入全为 `userName`，无一处用 ID |
| 是账号？ | **是** | `getCurrentUser()` = `getUserName()`；XML `#{userName}`；查询按 `userName` 等值 |
| 是姓名？ | **否** | `user_info` 另有姓名类字段，`user_name` 注释为"用户名"且 `isNull=false` |
| 可以机械替换成 `user_id` 吗？ | **不可以** | 用户表无 `user_id` 列；替换后所有按创建人过滤的查询静默返回空 |

### 代码答不了、必须 owner 裁定的

1. **账号可变更吗？** 若允许改名，历史 `create_by` 是保留旧账号（形成"孤儿"）还是级联更新？代码里没有改名逻辑，看不出答案。
2. **跨系统账号唯一性**：`create_by` 只存账号字符串，不含租户/来源。多来源 SSO 下同名账号是否冲突，需要业务确认。
3. **那 7 张无 `create_by` 的表**是否应补列（涉及 schema 变更，不只是差异清单）。
4. **`update_by` / `modify_by` 是否统一**——统一即变更，必须评估历史数据与双写兼容。

这四条写入 D-03 的待决清单，附本文件的证据行号即可逐条裁定。
