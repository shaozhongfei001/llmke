package com.gientech.ragqaservice.interfaces.resp;

import com.alibaba.fastjson2.JSONArray;
import com.gientech.ragcommon.index.enmus.DataSourceTypeEnum;
import lombok.Data;

import java.util.List;

/**
 * @author: shirleychen
 * @date 2025/9/2 13:08
 * @description
 */
@Data
public class DataReference {
    private String id;
    private RetrieveSqlData retrieveSqlData;
    private List<RetrieveTableData> retrieveTableDataList;


    @Data
    public static class RetrieveSqlData {

        private String fetchUrl;
        private String databaseName;
        private long total;
        private JSONArray preData;
        private String filePath;
    }

    @Data
    public static class RetrieveTableData {
        private String fetchUrl;
        private String databaseName;
        private String tableName;
        private String businessTableName;
        private long total;
        private String databaseType;
        private String dataSourceType;
        private Double score;
        private Long seq;
        private Long databaseId;
        private Long fileId;

        public String getFetchUrl() {
            if (dataSourceType.equals(DataSourceTypeEnum.DataTable.getCode())) {
                return String.format("/index/database/dataTable/queryTableFileData/%s", this.fileId);
            } else {
                return String.format("/index/database/directDB/queryTableData/%s/%s", this.databaseId, this.tableName);
            }

        }
    }
}
