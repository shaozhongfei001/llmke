package com.gientech.ragcommon.qa.dto;

import com.alibaba.fastjson2.annotation.JSONField;
import lombok.Data;
import org.apache.commons.lang3.StringUtils;

@Data
public class RerankModelDTO {

    /**
     * 模型名称
     */
    @JSONField(name = "model_name")
    private String modelName;

    /**
     * 模型url
     */
    private String url;

}
