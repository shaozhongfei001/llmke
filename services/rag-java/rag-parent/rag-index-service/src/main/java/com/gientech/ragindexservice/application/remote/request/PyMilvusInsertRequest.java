package com.gientech.ragindexservice.application.remote.request;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.gientech.ragcommon.index.dto.FileMetadataChunkDTO;
import com.gientech.ragcommon.index.FileChunkDTO;
import com.gientech.ragcommon.index.dto.ModelSimpDTO;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * @author: shirleychen
 * @date 2025/12/3 17:45
 * @description
 * "collection_name": "my_collection",
 *   "db_name" : "rag_knowledge_base",
 *   "document_list": [...]
 */
@Data
@AllArgsConstructor
@NoArgsConstructor
public class PyMilvusInsertRequest {
    @JsonProperty("collection_name")
    private String collectionName;
    @JsonProperty("db_name")
    private String dbName = "rag_knowledge_base";
    @JsonProperty("document_list")
    private List<FileChunkDTO> documentList;
    @JsonProperty("duplicate_flag")
    private Boolean duplicateFlag = false;
    @JsonProperty("model_name")
    private String modelName;

    public PyMilvusInsertRequest(String collectionName, List<FileChunkDTO> documentList, ModelSimpDTO modelInfo) {
        this.collectionName = collectionName;
        this.documentList = documentList;
        this.modelName = modelInfo.getModelName();
    }
}
