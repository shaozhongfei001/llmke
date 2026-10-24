package com.gientech.tools.database.infrastructure.util;

import java.util.List;

public class ExcelToMysqlUtil {
    /**
     * 生成MySQL建表语句
     */
    public static String generateCreateTableSql(String tableName, String tableComment, List<Object> rowCells) {
        // 构建建表语句
        StringBuilder sqlBuilder = new StringBuilder();
        sqlBuilder.append("CREATE TABLE `").append(tableName).append("` (\n");
        sqlBuilder.append("  `id` BIGINT AUTO_INCREMENT COMMENT '主键编号' ,\n");
        sqlBuilder.append("  `file_id` BIGINT   COMMENT '文件编号' ,\n");

        // 处理每个列
        for (int i = 0; i < rowCells.size(); i++) {
            sqlBuilder.append("  `").append("column_" + i).append("` ");
            sqlBuilder.append("VARCHAR(200) ");

            String columnComment = String.valueOf(rowCells.get(i));
            sqlBuilder.append("COMMENT '").append(truncateContent(columnComment, 1024)).append("' ");

            sqlBuilder.append(",\n");

            if (i == rowCells.size() - 1) {
                sqlBuilder.append("PRIMARY KEY (id)\n");
            }

        }

        sqlBuilder.append(") COMMENT = '").append(tableComment).append("';");

        return sqlBuilder.toString();
    }

    public static String truncateContent(String comment, int length) {
        if (comment == null) {
            return "";
        }
        return comment.length() > length ? comment.substring(0, length) : comment;
    }

    /**
     * 构建插入SQL语句
     */
    public static String buildInsertSql(String tableName, Long fileId, int columnCount) {
        StringBuilder sqlBuilder = new StringBuilder();
        sqlBuilder.append("INSERT INTO ").append(tableName).append(" (");
        sqlBuilder.append(" `file_id`, ");

        for (int i = 0; i < columnCount; i++) {
            sqlBuilder.append(" `").append("column_" + i).append("` ");

            if (i < columnCount - 1) {
                sqlBuilder.append(",");
            }
        }

        sqlBuilder.append(") VALUES (");
        sqlBuilder.append(fileId + ", ");
        for (int i = 0; i < columnCount; i++) {
            if (i > 0) {
                sqlBuilder.append(", ");
            }
            sqlBuilder.append("?");
        }

        sqlBuilder.append(")");
        return sqlBuilder.toString();
    }
}
