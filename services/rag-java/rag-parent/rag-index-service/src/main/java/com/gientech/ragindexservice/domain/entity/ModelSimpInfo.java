package com.gientech.ragindexservice.domain.entity;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

@Data
public class ModelSimpInfo {

    /**
     * 模型名称
     */
    @JsonProperty("model_name")
    private String modelName;

    /**
     * 模型的urlbaid
     */
    private String url;

    /**
     * APIkey
     */
    @JsonProperty(value = "key")
    private String apiKey;

    /**
     * 待接入的模型ID
     */
    @JsonProperty("model_id")
    private String modelIde;
}
