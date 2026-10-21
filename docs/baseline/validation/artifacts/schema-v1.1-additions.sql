-- LLMKE schema V1.1 增量表：引用证据落库
-- 为什么需要：contracts/evidence/llmke-citation-evidence.yaml 定义了 DocumentEvidence 的结构，
-- 但旧的 37 张表里没有任何地方能存"某段文本的哪一段是证据"。证据只存在内存里，
-- 一旦进程重启就无法复核，也无法做跨请求的重叠/重复检测。
--
-- 设计取舍：
--   * 不存原文，只存 (file_id, document_version, offset, text_hash)：原文属于文档存储，
--     重复存一份会导致"证据与原文不同步"这个经典问题；
--   * offset 单位显式落库（unicode_codepoint），避免将来换单位后历史数据不可解释；
--   * 主键用 evidence_id（业务幂等键），天然去重；
--   * idx_doc_range 支撑"同一文档版本内按区间查"，也是重叠检测的执行基础。

CREATE TABLE IF NOT EXISTS `document_evidence` (
  `evidence_id`      VARCHAR(128) NOT NULL COMMENT '证据幂等键',
  `kb_id`            VARCHAR(64)  NOT NULL COMMENT '知识库',
  `file_id`          VARCHAR(64)  NOT NULL COMMENT '文件',
  `document_version` VARCHAR(64)  NOT NULL COMMENT '文档版本（解析器版本变化必须升版本）',
  `chunk_id`         VARCHAR(64)  NOT NULL COMMENT '分块',
  `content_hash`     CHAR(64)     NOT NULL COMMENT '整篇文档内容哈希',
  `offset_start`     INT UNSIGNED NOT NULL COMMENT '起始码点偏移（左闭）',
  `offset_end`       INT UNSIGNED NOT NULL COMMENT '结束码点偏移（右开）',
  `offset_unit`      VARCHAR(32)  NOT NULL DEFAULT 'unicode_codepoint' COMMENT '偏移单位',
  `text_hash`        CHAR(64)     NOT NULL COMMENT '该区间文本哈希（用于回读校验，防篡改）',
  `parser_version`   VARCHAR(64)  NOT NULL COMMENT '解析器版本',
  `created_at`       DATETIME(3)  NOT NULL,
  `created_by`       VARCHAR(64)  NOT NULL,
  PRIMARY KEY (`evidence_id`),
  KEY `idx_doc_range` (`kb_id`,`file_id`,`document_version`,`offset_start`),
  KEY `idx_chunk` (`chunk_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
  COMMENT='引用证据：只存定位与哈希，不复制原文';
