-- LLMKE schema V1.2 增量：文档分块落库
--
-- 为什么需要：
--   证据（document_evidence）只存定位与哈希，不存原文；但检索与回答需要原文。
--   分块是"解析产物"，与原文不同——它带 chunk_strategy 与 parser_version，
--   这两个版本任何变化都会让下游 embedding 失效，因此必须落库并参与版本判定。
--
-- 设计取舍：
--   * 存 text：分块是检索单元，每次回表取原文会让召回路径多一跳；且分块是派生数据，
--     与"证据不复制原文"的原则不冲突（证据复制的是文档原文，分块本身就是派生物）。
--   * text_hash 与 document_evidence.text_hash 同算法（sha256 over utf-8 码点子串），
--     这样"分块 → 证据"可以直接过契约校验，不需要额外换算。
--   * (kb_id,file_id,document_version,chunk_index) 唯一：同一文档版本内分块序号不能重复，
--     否则重建时会出现两份内容不同的同名分块。

CREATE TABLE IF NOT EXISTS `document_chunk` (
  `chunk_id`         VARCHAR(128) NOT NULL COMMENT '分块幂等键',
  `kb_id`            VARCHAR(64)  NOT NULL,
  `file_id`          VARCHAR(64)  NOT NULL,
  `document_version` VARCHAR(64)  NOT NULL,
  `chunk_index`      INT UNSIGNED NOT NULL COMMENT '同文档版本内序号（从 0 起）',
  `offset_start`     INT UNSIGNED NOT NULL COMMENT '起始码点（左闭）',
  `offset_end`       INT UNSIGNED NOT NULL COMMENT '结束码点（右开）',
  `offset_unit`      VARCHAR(32)  NOT NULL DEFAULT 'unicode_codepoint',
  `text`             MEDIUMTEXT   NOT NULL COMMENT '分块原文（派生数据）',
  `text_hash`        CHAR(64)     NOT NULL COMMENT 'sha256(text)，与证据同算法',
  `content_hash`     CHAR(64)     NOT NULL COMMENT '整篇文档内容哈希',
  `parser_version`   VARCHAR(64)  NOT NULL,
  `chunk_strategy`   VARCHAR(64)  NOT NULL COMMENT '分块策略标识（含参数摘要）',
  `created_at`       DATETIME(3)  NOT NULL,
  `created_by`       VARCHAR(64)  NOT NULL,
  PRIMARY KEY (`chunk_id`),
  UNIQUE KEY `uniq_doc_index` (`kb_id`,`file_id`,`document_version`,`chunk_index`),
  KEY `idx_doc_range` (`kb_id`,`file_id`,`document_version`,`offset_start`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
  COMMENT='文档分块：解析产物，带策略与解析器版本';
