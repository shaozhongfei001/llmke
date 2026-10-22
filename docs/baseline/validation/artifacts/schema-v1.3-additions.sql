-- LLMKE schema V1.3 增量：索引代次 / 激活指针 / 写租约 / outbox
--
-- 依据 docs/baseline/validation/P0-04-DESIGN-PROPOSAL.md（状态：PROPOSED，待 index-owner 裁定）。
-- 本文件是"参考实现"的表结构：机制可按此验证，但**粒度与租约时长等参数仍待裁定**。
--
-- 为什么必须落库而不是只写在代码里：
--   S2（切换中断）与 S4（迟到重试）的判据都是"某个 UPDATE 影响了 0 行还是 1 行"，
--   只有真实数据库的原子性才能验证；用内存 mock 验证这两条等于没验证。

CREATE TABLE IF NOT EXISTS `index_generation` (
  `generation_id`     BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `kb_id`             VARCHAR(64)  NOT NULL,
  `content_hash`      CHAR(64)     NOT NULL COMMENT '本代内容清单指纹',
  `document_version`  VARCHAR(64)  NOT NULL,
  `parse_version`     VARCHAR(64)  NOT NULL,
  `chunk_version`     VARCHAR(64)  NOT NULL,
  `embedding_version` VARCHAR(64)  NOT NULL,
  `physical_locations` JSON        NOT NULL COMMENT '各存储物理位置（vector/es/graph/...）',
  `manifest_json`     JSON         NOT NULL COMMENT '逐文档逐块清单，写入后不可改',
  `state`             VARCHAR(16)  NOT NULL COMMENT 'BUILDING/VALIDATING/READY/ACTIVE/RETIRED/ABORTED',
  `created_at`        DATETIME(3)  NOT NULL,
  `created_by`        VARCHAR(64)  NOT NULL,
  PRIMARY KEY (`generation_id`),
  UNIQUE KEY `uniq_kb_content` (`kb_id`,`content_hash`),
  KEY `idx_kb_state` (`kb_id`,`state`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
  COMMENT='索引代次：不可变清单（只允许改 state）';

CREATE TABLE IF NOT EXISTS `index_generation_activation` (
  `kb_id`                  VARCHAR(64) NOT NULL,
  `generation_id`          BIGINT UNSIGNED NOT NULL,
  `previous_generation_id` BIGINT UNSIGNED NULL,
  `activated_at`           DATETIME(3) NOT NULL,
  `activated_by`           VARCHAR(64) NOT NULL,
  PRIMARY KEY (`kb_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
  COMMENT='单行激活指针：切换只能整体成功或整体不变';

CREATE TABLE IF NOT EXISTS `index_write_lease` (
  `kb_id`         VARCHAR(64) NOT NULL,
  `generation_id` BIGINT UNSIGNED NOT NULL,
  `lease_token`   BIGINT UNSIGNED NOT NULL COMMENT '单调递增，写入必须携带',
  `owner`         VARCHAR(128) NOT NULL,
  `expires_at`    DATETIME(3) NOT NULL,
  `updated_at`    DATETIME(3) NOT NULL,
  PRIMARY KEY (`kb_id`,`generation_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
  COMMENT='写租约：fencing token + 过期回收';

CREATE TABLE IF NOT EXISTS `index_outbox` (
  `id`              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `aggregate`       VARCHAR(64) NOT NULL,
  `aggregate_id`    VARCHAR(64) NOT NULL,
  `event_type`      VARCHAR(64) NOT NULL,
  `payload_json`    JSON NOT NULL,
  `state`           VARCHAR(16) NOT NULL COMMENT 'PENDING/SENT/FAILED',
  `attempts`        INT NOT NULL DEFAULT 0,
  `next_attempt_at` DATETIME(3) NOT NULL,
  `created_at`      DATETIME(3) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_state_next` (`state`,`next_attempt_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
  COMMENT='同库事务投递：业务写入与事件写入同一事务';
