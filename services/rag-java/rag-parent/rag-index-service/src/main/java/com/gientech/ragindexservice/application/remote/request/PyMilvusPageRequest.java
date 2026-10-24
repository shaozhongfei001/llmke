package com.gientech.ragindexservice.application.remote.request;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonValue;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * @author: shirleychen
 * @date 2025/12/2 19:51
 * @description
 * {
 *   "collection_name_list": ["table_chunks_测试模型替换"],
 *   "expr": "",
 *   "page_no": 1,
 *   "page_num": 100
 * }
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class PyMilvusPageRequest {
    @JsonProperty("collection_name_list")
    private List<String> collectionNameList;
    @JsonProperty("col_name")
    private String colName = "file_id";
    @JsonProperty("col_values")
    private List<String> colValues;
    @JsonProperty("page_no")
    private Long pageNo;
    @JsonProperty("page_num")
    private Long pageSize;
    @JsonProperty("db_name")
    private String dbName = "rag_knowledge_base";

    public PyMilvusPageRequest(String collectionName, Long fileId, Long pageNo, Long pageSize) {
        this.collectionNameList = List.of(collectionName);
        this.colValues = List.of(String.valueOf(fileId));
        this.pageNo = pageNo;
        this.pageSize = pageSize;
    }
}
