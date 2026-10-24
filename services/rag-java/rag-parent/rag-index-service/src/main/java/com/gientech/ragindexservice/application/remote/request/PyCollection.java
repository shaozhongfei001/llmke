package com.gientech.ragindexservice.application.remote.request;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.gientech.ragcommon.index.dto.ModelSimpDTO;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * @author: shirleychen
 * @date 2025/12/2 20:21
 * @description
 */
@Data
@AllArgsConstructor
@NoArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class PyCollection {
    @JsonProperty("collection_name")
    private String collectionName;
    @JsonProperty("db_name")
    private String dbName = "rag_knowledge_base";
    @JsonProperty("model_name")
    private String modelName;
    @JsonProperty("col_name")
    private String colName;
    @JsonProperty("col_values")
    private List<String> colValues;

    public PyCollection(String collectionName, ModelSimpDTO embeddingModelInfo) {
        this.collectionName = collectionName;
        this.modelName = embeddingModelInfo.getModelName();
    }

    public PyCollection(String collectionName, Long fileId) {
        this.collectionName = collectionName;
        this.colName = "file_id";
        this.colValues = List.of(String.valueOf(fileId));
    }

    public PyCollection(String collectionName) {
        this.collectionName = collectionName;
    }
}
