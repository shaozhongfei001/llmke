package com.gientech.elasticsearchservice.document;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Date;

/**
 * @Description:
 * @Author: chenjuan
 * @Date: 2024/9/20 13:16
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class FullTextDoc {

    @JsonProperty("page_content")
    private String pageContent;

    @JsonProperty("metadata")
    private MetaData metaData;

    public static FullTextDoc getDefault() {
        FullTextDoc fullTextDoc = new FullTextDoc();
        MetaData metaData = new MetaData();
        metaData.init();
        fullTextDoc.setMetaData(metaData);
        return fullTextDoc;
    }

}
