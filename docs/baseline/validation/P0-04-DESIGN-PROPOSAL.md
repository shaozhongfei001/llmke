# P0-04 设计提案：代次 / 激活指针 / fencing / 租约

日期：2026-10-22　状态：**PROPOSED**，需 `index-owner` 裁定后才可冻结并实现
依据：`P0-04-READINESS.md` 的实测结论——现有代码**四类机制全缺**，仅任务领取有 id 级 CAS。

> 本提案不实现任何业务逻辑，只定义"要使 S1–S5 可验证，必须先有什么"。
> 表结构是提案草案，需随 schema V1.2 一起冻结。

---

## 1. 四个缺口与对应设计

| 缺口（实测） | 设计 | 解决哪个场景 |
|---|---|---|
| 无 generation 概念 | `index_generation`（不可变清单） | S1 部分后端失败、S3 内容覆盖 |
| 无原子激活指针 | `index_generation_activation`（单行 CAS 切换） | S2 切换中断、S5 旧服务回退 |
| 无 fencing token | `index_write_lease`（带 token 的租约） | S4 迟到重试 |
| 无 outbox/补偿 | `index_outbox`（同库事务内投递） | 全部场景的失败回溯 |

---

## 2. 表设计（草案）

### 2.1 `index_generation` —— 不可变代次清单

```sql
CREATE TABLE `index_generation` (
  `generation_id`   BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `kb_id`           VARCHAR(64)  NOT NULL,
  `content_hash`    CHAR(64)     NOT NULL COMMENT '本代内容清单哈希（manifest 自身指纹）',
  `document_version` VARCHAR(64) NOT NULL,
  `parse_version`   VARCHAR(64)  NOT NULL,
  `chunk_version`   VARCHAR(64)  NOT NULL,
  `embedding_version` VARCHAR(64) NOT NULL,
  `physical_locations` JSON       NOT NULL COMMENT '各存储物理位置（vector/es/graph/...）',
  `manifest_json`   JSON          NOT NULL COMMENT '逐文档逐块的完整清单',
  `state`           VARCHAR(16)   NOT NULL COMMENT 'BUILDING/VALIDATING/READY/ACTIVE/RETIRED',
  `created_at`      DATETIME(3)   NOT NULL,
  `created_by`      VARCHAR(64)   NOT NULL,
  PRIMARY KEY (`generation_id`),
  UNIQUE KEY `uniq_kb_content` (`kb_id`,`content_hash`),
  KEY `idx_kb_state` (`kb_id`,`state`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```

要点：

- **不可变**：写入后除 `state` 外不允许改；`manifest_json` 一旦写入即冻结（应用层禁止 UPDATE）；
- `uniq_kb_content` 让"同内容重复构建"天然幂等；
- `physical_locations` 单独存，便于 S1 判断"哪几个后端已完成"。

### 2.2 `index_generation_activation` —— 单行原子指针

```sql
CREATE TABLE `index_generation_activation` (
  `kb_id`         VARCHAR(64) NOT NULL,
  `generation_id` BIGINT UNSIGNED NOT NULL,
  `activated_at`  DATETIME(3) NOT NULL,
  `activated_by`  VARCHAR(64) NOT NULL,
  `previous_generation_id` BIGINT UNSIGNED NULL,
  PRIMARY KEY (`kb_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```

切换语义（**单行 CAS，不逐后端切换**）：

```sql
UPDATE index_generation_activation
   SET generation_id = :new, previous_generation_id = generation_id,
       activated_at = NOW(3), activated_by = :who
 WHERE kb_id = :kb AND generation_id = :expected_old;
-- 影响行数=1 才算切换成功；=0 说明别人先切了，必须重新读
```

这样 S2「切换中断」有了明确判据：**要么指针指旧代、要么指新代，不存在"一半新一半旧"**。

### 2.3 `index_write_lease` —— 带 fencing 的租约

```sql
CREATE TABLE `index_write_lease` (
  `kb_id`         VARCHAR(64) NOT NULL,
  `generation_id` BIGINT UNSIGNED NOT NULL,
  `lease_token`   BIGINT UNSIGNED NOT NULL COMMENT '单调递增，写入必须携带',
  `owner`         VARCHAR(128) NOT NULL COMMENT 'worker 标识',
  `expires_at`    DATETIME(3) NOT NULL,
  PRIMARY KEY (`kb_id`,`generation_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```

写入时必须校验：

```sql
UPDATE ... SET ... WHERE kb_id=:kb AND generation_id=:gen AND :token = (
    SELECT lease_token FROM index_write_lease WHERE kb_id=:kb AND generation_id=:gen);
```

- token 只增不减 → 旧 worker 的 token 一定小于当前值，写入被拒（S4 迟到重试）；
- `expires_at` 提供**超时回收**（补上现有代码"status=1 卡死"的洞）。

### 2.4 `index_outbox` —— 同库事务投递

```sql
CREATE TABLE `index_outbox` (
  `id`            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `aggregate`     VARCHAR(64) NOT NULL COMMENT 'kb / file / task',
  `aggregate_id`  VARCHAR(64) NOT NULL,
  `event_type`    VARCHAR(64) NOT NULL,
  `payload_json`  JSON NOT NULL,
  `state`         VARCHAR(16) NOT NULL COMMENT 'PENDING/SENT/FAILED',
  `attempts`      INT NOT NULL DEFAULT 0,
  `next_attempt_at` DATETIME(3) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_state_next` (`state`,`next_attempt_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
```

要点：事件写入与业务写入在**同一个本地事务**里，避免"业务成功、消息丢失"。

---

## 3. 状态机（generation）

```
BUILDING ──> VALIDATING ──> READY ──> ACTIVE ──> RETIRED
    │             │            │
    └──失败───────┴──失败──> ABORTED（保留记录，供 S1 复盘）
```

约束：

- 只有 `READY` 才能被激活；
- 激活即把旧的 `ACTIVE` 改为 `RETIRED`（同事务）；
- `RETIRED` 之前必须保证 `previous_generation_id` 仍可读（S5 回退需要）。

---

## 4. S1–S5 变成可执行判据（这是本提案的核心价值）

| 场景 | 判据（可写成测试） |
|---|---|
| **S1 部分后端失败** | 构建后 `physical_locations` 缺任一项 → generation 必须停在 `VALIDATING`/`ABORTED`，**不得进入 READY**；激活指针不变 |
| **S2 切换中断** | 强行在切换语句执行后 kill 进程 → 重启后读指针必须是"完整旧代"或"完整新代"（单行 CAS 保证），且 `previous_generation_id` 正确 |
| **S3 内容覆盖** | 同 `kb_id+file_id` 但 `content_hash` 变化时，旧 generation 的 manifest 必须仍可按 `generation_id` 查出旧版本，不被覆盖 |
| **S4 迟到重试** | 用过期 token 写入 → 影响行数必须为 0；用当前 token 写入 → 1 |
| **S5 旧服务回退** | 把指针 CAS 回 `previous_generation_id` → 读取路径立即回到旧代，且旧代 manifest 完整 |

每条都能落成一个自动化测试（S2 可用"两个连接、交错执行"模拟中断）。

---

## 5. 与现有代码的关系

- 现有 `ReEmbeddingRetryTaskServiceImpl.getRetryTask()` 的 CAS 可**保留**，但必须补：
  1. `lease_token`（当前没有 → 无法拒绝迟到写入）；
  2. `expires_at` + 回收任务（当前 `status=1` 永不回退 → 僵尸任务）；
- 新增的 4 张表属"加表不改表"，与设计文档 5.2 的"加表不改表"原则一致；
- 本提案不要求改动现有 37 张表。

---

## 6. 需要 `index-owner` 裁定的点

| # | 问题 | 为什么必须 owner 定 |
|---|---|---|
| 1 | manifest 是否覆盖全部后端（vector/es/graph/fulltext） | 取决于实际部署形态 |
| 2 | generation 是否按 KB 粒度（本提案假设是） | 也可能是"全库一代" |
| 3 | 租约时长与续约方式 | 取决于单批处理耗时 |
| 4 | S5 回退是否允许跨代（保留几代） | 关系到存储成本 |
| 5 | 旧 worker 的写入是"拒绝"还是"记录后丢弃" | 关系到审计需求 |

裁定后本提案升为 `SCHEMA V1.2`，并按 §4 实现 5 条测试。
