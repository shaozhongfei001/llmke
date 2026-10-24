package com.gientech.ragindexservice.application.remote.response;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.gientech.ragcommon.index.FileChunkDTO;
import com.gientech.ragcommon.index.dto.FileMetadataChunkDTO;
import lombok.Data;

import java.util.List;

/**
 * @author: shirleychen
 * @date 2025/12/2 19:55
 * @description
 */
@Data
public class PyMilvusResultData {
    @JsonProperty("result_data")
    private List<FileChunkDTO> resultData;
    private Long total;
}
