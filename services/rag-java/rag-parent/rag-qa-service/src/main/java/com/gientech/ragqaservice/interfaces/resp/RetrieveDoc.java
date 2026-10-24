package com.gientech.ragqaservice.interfaces.resp;

import com.alibaba.fastjson2.reader.ObjectReaderImplJSONP;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

import java.util.List;

/**
 * @author chenjuan
 * @date 2025/6/24 11:16
 */
@Data
public class RetrieveDoc {
    @JsonProperty("page_content")
    private String pageContent;
    private RetrieveMetaData metadata;
    @JsonProperty("order_num")
    private String orderNum;
    @JsonProperty("converted_file_path")
    private String convertedFilePath;
    @JsonProperty("parsed_file_path")
    private String parsedFilePath;
    @JsonProperty("rrf_score")
    private Double rrfScore;
    @JsonProperty("rrf_score_rank")
    private Integer rrfScoreRank;
    private String type;
    @JsonProperty("pic_url_list")
    private List<String> picUrlList;
    private Long pk;
    private Integer pdfPages;
    private Object offset;


    @Data
    public static class RetrieveMetaData {
        private String source;
        @JsonProperty("file_path")
        private String filePath;
        private String id;
        @JsonProperty("search_type")
        private List<String> searchType;
        private List<List<Long>> offset;
        private Object position;
        @JsonProperty("chunk_type")
        private String chunkType;
        @JsonProperty("file_id")
        private Long fileId;
        @JsonProperty("table_name")
        private String tableName;
        @JsonProperty("chunk_index")
        private Long chunkIndex;
        @JsonProperty("table_summary_id")
        private Long tableSummaryId;
        @JsonProperty("labels")
        private List<String> labels;
        @JsonProperty("page_number")
        private List<Integer> pageNumber;
        @JsonProperty("page_size")
        private Object pageSize;
        @JsonProperty("pic_offset_list")
        private Object picOffsetList;
        @JsonProperty("business_name")
        private String businessName;
        @JsonProperty("physical_name")
        private String physicalName;
        @JsonProperty("database_name")
        private String databaseName;
        @JsonProperty("row_count")
        private Long rowCount;
        @JsonProperty("database_description")
        private String databaseDescription;
        @JsonProperty("database_id")
        private Long databaseId;
        @JsonProperty("column_count")
        private Long columnCount;
        private SearchInfo search;
        private Double score;
        @JsonProperty("rerank_score_rank")
        private Long rerankScoreRank;
        private String description;
        private Integer permission;
        private String columns;
        @JsonProperty("create_time")
        private String createTime;
        @JsonProperty("update_time")
        private String updateTime;

        @Data
        public static class SearchInfo {
            private List<String> type;
            private String query;
            private List<Long> rank;
        }
    }
}
