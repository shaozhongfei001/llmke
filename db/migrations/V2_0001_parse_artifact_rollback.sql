-- V2_0001 回退：撤掉快照身份列与索引。
--
-- 幂等：先判存在再删；重复执行不报错。
-- 只删本迁移加的列，不碰既有列 —— 回退范围必须与正迁移严格对称。

DROP PROCEDURE IF EXISTS v2_drop_index_if_exists;
DROP PROCEDURE IF EXISTS v2_drop_column_if_exists;

DELIMITER $$

CREATE PROCEDURE v2_drop_index_if_exists(IN p_table VARCHAR(64), IN p_index VARCHAR(64))
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.statistics
               WHERE table_schema = DATABASE() AND table_name = p_table
                 AND index_name = p_index) THEN
        SET @v2_sql = CONCAT('ALTER TABLE `', p_table, '` DROP INDEX `', p_index, '`');
        PREPARE v2_stmt FROM @v2_sql;
        EXECUTE v2_stmt;
        DEALLOCATE PREPARE v2_stmt;
    END IF;
END$$

CREATE PROCEDURE v2_drop_column_if_exists(IN p_table VARCHAR(64), IN p_column VARCHAR(64))
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_schema = DATABASE() AND table_name = p_table
                 AND column_name = p_column) THEN
        SET @v2_sql = CONCAT('ALTER TABLE `', p_table, '` DROP COLUMN `', p_column, '`');
        PREPARE v2_stmt FROM @v2_sql;
        EXECUTE v2_stmt;
        DEALLOCATE PREPARE v2_stmt;
    END IF;
END$$

DELIMITER ;

CALL v2_drop_index_if_exists('knowledge_base_list', 'idx_kbl_parse_artifact');
CALL v2_drop_index_if_exists('knowledge_base_list', 'idx_kbl_content_uid');
CALL v2_drop_index_if_exists('file_parse_task', 'idx_fpt_parse_artifact');

CALL v2_drop_column_if_exists('knowledge_base_list', 'artifact_generation');
CALL v2_drop_column_if_exists('knowledge_base_list', 'parse_artifact_id');
CALL v2_drop_column_if_exists('knowledge_base_list', 'content_uid');
CALL v2_drop_column_if_exists('file_parse_task', 'artifact_generation');
CALL v2_drop_column_if_exists('file_parse_task', 'parse_artifact_id');
CALL v2_drop_column_if_exists('file_parse_task', 'content_uid');

DROP PROCEDURE IF EXISTS v2_drop_index_if_exists;
DROP PROCEDURE IF EXISTS v2_drop_column_if_exists;
