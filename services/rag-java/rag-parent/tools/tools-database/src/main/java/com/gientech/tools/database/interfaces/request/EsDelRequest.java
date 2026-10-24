package com.gientech.tools.database.interfaces.request;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

/**
 * @author: shirleychen
 * @date 2025/9/16 17:26
 * @description
 */
@Data
public class EsDelRequest {
    @JsonProperty("index_name")
    private String indexName;
}
