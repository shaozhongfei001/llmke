package com.gientech.ragcommon.index.dto;

import com.alibaba.fastjson2.annotation.JSONField;
import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import org.springframework.util.StringUtils;

@Schema(name = "模型信息")
@Data
public class ModelSimpDTO {

    @Schema(name = "modelName", description = "模型名称")
    @JsonProperty("model_name")
    @JSONField(name = "model_name")
    private String modelName;

    @Schema(name = "url", description = "模型url")
    private String url;

    @Schema(name = "apiKey", description = "模型key")
    @JsonProperty(value = "key")
    @JSONField(name = "key")
    private String apiKey;

    @Schema(name = "modelIde", description = "待接入的模型ID")
    @JsonProperty("model_id")
    @JSONField(name = "model_id")
    private String modelIde;

    public String getApiKey() {
        if(StringUtils.isEmpty(apiKey))
            return "";
        return apiKey;
    }
}
