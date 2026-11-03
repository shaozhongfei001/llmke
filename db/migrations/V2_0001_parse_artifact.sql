-- V2_0001：把"解析快照身份"挂到文件台账与解析任务上。
--
-- 为什么需要
--   V2 的快照（ParseArtifact）是内容寻址的：同一个 content_uid 可能有多次产出（换解析器/
--   换配置/换模板），必须能回答"这条文件当前挂的是哪一次产物"。没有这层，撤权/重传/回退
--   只能靠时间猜，属于 U-07 要求验证的迁移对象。
--
-- 幂等：MySQL 8 没有 ADD COLUMN IF NOT EXISTS，这里用 information_schema 判定后动态执行，
--   重复执行不报错、不重复加列。回退见同名 _rollback.sql。
--
-- 安全：只加可空列和普通索引，不改既有列类型、不动数据、不建外键（避免锁表与跨表依赖）。

DROP PROCEDURE IF EXISTS v2_add_column_if_missing;
DROP PROCEDURE IF EXISTS v2_add_index_if_missing;

DELIMITER $$

CREATE PROCEDURE v2_add_column_if_missing(IN p_table VARCHAR(64), IN p_column VARCHAR(64),
                                          IN p_ddl TEXT)
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_schema = DATABASE() AND table_name = p_table
                     AND column_name = p_column) THEN
        SET @v2_sql = CONCAT('ALTER TABLE `', p_table, '` ADD COLUMN ', p_ddl);
        PREPARE v2_stmt FROM @v2_sql;
        EXECUTE v2_stmt;
        DEALLOCATE PREPARE v2_stmt;
    END IF;
END$$

CREATE PROCEDURE v2_add_index_if_missing(IN p_table VARCHAR(64), IN p_index VARCHAR(64),
                                         IN p_cols VARCHAR(255))
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.statistics
                   WHERE table_schema = DATABASE() AND table_name = p_table
                     AND index_name = p_index) THEN
        SET @v2_sql = CONCAT('ALTER TABLE `', p_table, '` ADD INDEX `', p_index, '` (', p_cols, ')');
        PREPARE v2_stmt FROM @v2_sql;
        EXECUTE v2_stmt;
        DEALLOCATE PREPARE v2_stmt;
    END IF;
END$$

DELIMITER ;

-- 文件台账：当前生效的快照与内容身份
CALL v2_add_column_if_missing('knowledge_base_list', 'content_uid',
    '`content_uid` char(64) NULL COMMENT ''原文内容 sha256（内容寻址，跨版本稳定）''');
CALL v2_add_column_if_missing('knowledge_base_list', 'parse_artifact_id',
    '`parse_artifact_id` varchar(64) NULL COMMENT ''当前生效 ParseArtifact（V2 快照）''');
CALL v2_add_column_if_missing('knowledge_base_list', 'artifact_generation',
    '`artifact_generation` int NULL COMMENT ''快照代次；同内容多次产出的序号''');

-- 解析任务：这次任务产出/期望的快照，便于失败重试与回退定位
CALL v2_add_column_if_missing('file_parse_task', 'content_uid',
    '`content_uid` char(64) NULL COMMENT ''本次任务的内容身份''');
CALL v2_add_column_if_missing('file_parse_task', 'parse_artifact_id',
    '`parse_artifact_id` varchar(64) NULL COMMENT ''本次任务产出/消费的快照''');
CALL v2_add_column_if_missing('file_parse_task', 'artifact_generation',
    '`artifact_generation` int NULL COMMENT ''本次任务对应的快照代次''');

CALL v2_add_index_if_missing('knowledge_base_list', 'idx_kbl_parse_artifact', '`parse_artifact_id`');
CALL v2_add_index_if_missing('knowledge_base_list', 'idx_kbl_content_uid', '`content_uid`');
CALL v2_add_index_if_missing('file_parse_task', 'idx_fpt_parse_artifact', '`parse_artifact_id`');

DROP PROCEDURE IF EXISTS v2_add_column_if_missing;
DROP PROCEDURE IF EXISTS v2_add_index_if_missing;
