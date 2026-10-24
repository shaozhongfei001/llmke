package com.gientech.ragqaservice.application.service.entity;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

import java.io.Serializable;

/**
 * @author chenjuan
 * @date 2025/4/24 10:12
 */
@Data
public class ModelInfoRequest implements Serializable {
    @JsonProperty("model_name")
    private String modelName;
    private String url;
    private String key;
    @JsonProperty("model_id")
    private String modelId;
}
