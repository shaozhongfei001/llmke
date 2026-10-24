package com.gientech.ragcommon.index;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.gientech.ragcommon.index.dto.FileMetadataChunkDTO;
import lombok.Data;

/**
 * @author: shirleychen
 * @date 2025/12/3 18:03
 * @description
 */
@Data
public class FileChunkDTO {
    @JsonProperty("page_content")
    private String pageContent;
    private FileMetadataChunkDTO metadata;
}
