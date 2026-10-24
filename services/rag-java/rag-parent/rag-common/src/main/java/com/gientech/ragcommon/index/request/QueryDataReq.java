package com.gientech.ragcommon.index.request;

import com.alibaba.fastjson.JSON;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import javax.management.Query;

@Schema(name = "执行sql查询数据的参数")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class QueryDataReq {
    /**
     * 数据库编号
     */
    @Schema(name = "databaseId", description = "数据库编号")
    private Long databaseId;

    /**
     * 执行sql
     */
    @Schema(name = "sql", description = "执行sql")
    private String sql;

    @Schema(name = "sqlQueryInfo", description = "对话中调用sql查数据，定位到具体对话")
    private SqlQueryInfo sqlQueryInfo;

    public String getSql(){
        return sql.replaceAll(";\\s*$","");
    }

    @Data
    public static class SqlQueryInfo {
        private Long dialogueId;

        public String getSqlQueryKey() {
            return String.format("sql-data:%s", dialogueId);
        }
    }


    public static QueryDataReq from(String sql, Long databaseId, Long dialogueId) {
        QueryDataReq queryDataReq = new QueryDataReq();
        queryDataReq.setSql(sql);
        queryDataReq.setDatabaseId(databaseId);
        QueryDataReq.SqlQueryInfo sqlQueryInfo = new QueryDataReq.SqlQueryInfo();
        sqlQueryInfo.setDialogueId(dialogueId);
        queryDataReq.setSqlQueryInfo(sqlQueryInfo);
        return queryDataReq;
    }

}
