package com.gientech.ragqaservice.interfaces.resp;

import cn.hutool.db.Entity;
import com.fasterxml.jackson.annotation.JsonIgnore;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

import java.util.List;

/**
 * @author: shirleychen
 * @date 2025/9/18 17:54
 * @description
 */
@Data
public class SqlMetaData {
    @JsonProperty("table_result_data")
    private TableResultData tableResultData;
    @JsonProperty("database_documents")
    private List<RetrieveDoc> databaseDocuments;
    @JsonIgnore
    private RetrieveSqlDataReference retrieveSqlDataReference;

    @Data
    public static class TableResultData {
        @JsonProperty("row_count")
        private int rowCount;
        @JsonProperty("column_count")
        private int columnCount;
        @JsonProperty("head_n_row")
        private List<Entity> headNRow;
    }
}
