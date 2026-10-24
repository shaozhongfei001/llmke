package com.gientech.ragindexservice.application.remote.request;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.gientech.ragcommon.index.dto.FileMetadataChunkDTO;
import com.gientech.ragcommon.index.dto.ModelSimpDTO;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.checkerframework.checker.units.qual.N;

import java.util.List;

/**
 * @author: shirleychen
 * @date 2025/11/21 15:06
 * @description
 */
@Data
@AllArgsConstructor
@NoArgsConstructor
public class PyMilvusUpdateDocRequest {
    @JsonProperty("index_name")
    private String indexName;
    @JsonProperty("document_list")
    private List<FileMetadataChunkDTO> documentList;
    @JsonProperty("embedding_model_info")
    private ModelSimpDTO embeddingModelInfo;
}
