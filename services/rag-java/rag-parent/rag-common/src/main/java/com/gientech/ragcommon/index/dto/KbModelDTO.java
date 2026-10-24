package com.gientech.ragcommon.index.dto;

import com.alibaba.fastjson2.annotation.JSONField;
import lombok.Data;
import org.apache.commons.lang3.StringUtils;

@Data
public class KbModelDTO {

    /**
     * 模型名称
     */
    @JSONField(name = "model_name")
    private String modelName;

    /**
     * 模型url
     */
    private String url;

    /**
     * 模型key
     */
    private String key;

    /**
     * 模型id
     */
    @JSONField(name = "model_id")
    private String modelId;

    public String getKey() {
        return StringUtils.isNotBlank(key) ? key : "";
    }
}
