package com.gientech.ragqaservice.interfaces.resp;

import cn.hutool.db.Entity;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

import java.util.List;

/**
 * @author: shirleychen
 * @date 2025/9/2 10:31
 * @description
 */
@Data
public class RetrieveSql {
    private String sql;
    @JsonProperty("database_id")
    private Long databaseId;
    @JsonProperty("table_name")
    private String tableName;

    public String getSql(){
        return sql.replaceAll(";\\s*$","");
    }
}
