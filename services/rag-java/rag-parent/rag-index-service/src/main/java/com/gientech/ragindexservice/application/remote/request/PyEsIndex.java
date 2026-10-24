package com.gientech.ragindexservice.application.remote.request;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

import java.util.List;

/**
 * @author: shirleychen
 * @date 2025/12/5 18:20
 * @description
 */
@Data
@JsonInclude(JsonInclude.Include.NON_NULL)
public class PyEsIndex {
    @JsonProperty("index_name")
    private String indexName;
    @JsonProperty("col_name")
    private String colName = "document_id";
    @JsonProperty("col_values")
    private List<String> colValues;

    public PyEsIndex(String indexName) {
        this.indexName = indexName;
    }

    public PyEsIndex(String indexName, Long fileId) {
        this.indexName = indexName;
        this.colValues = List.of(String.valueOf(fileId));
    }
}
