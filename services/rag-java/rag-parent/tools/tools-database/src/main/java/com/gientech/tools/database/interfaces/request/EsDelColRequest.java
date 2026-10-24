package com.gientech.tools.database.interfaces.request;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

import java.util.List;

/**
 * @author: shirleychen
 * @date 2025/9/16 17:48
 * @description
 */
@Data
public class EsDelColRequest {
    @JsonProperty("index_name")
    private String indexName;
    @JsonProperty("condition_json")
    private List<ConditionJson> conditionJson;


    @Data
    public static class ConditionJson {
        @JsonProperty("physical_name")
        private List<String> physicalName;
    }
}
