package com.gientech.ragcommon.qa.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

import java.util.List;

@Schema(name = "配置添加请求参数",requiredProperties = {"configJson","name"})
@Data
public class SearchConfigAddReq {

    @Schema(name = "isDefault", description = "是否默认 0:否；1:是 ")
    private Integer isDefault = 0;

    @Schema(name = "enabledFaq", description = "是否开启faq(0:否;1:是)")
    private Integer enabledFaq = 0;

    @Schema(name = "dependOnKb", description = "是否强依赖知识库(0:否;1:是)")
    private Integer dependOnKb = 0;

    @Schema(name = "configJson", description = "配置详情")
    @NotBlank(message = "configJson不能为空")
    private String configJson;

    @Schema(name = "sensitiveWordIds", description = "敏感词id")
    private String sensitiveWordIds;

    @Schema(name = "defaultAnswer", description = "默认回答(sensitive_word_ids不为空时,必填)")
    private String defaultAnswer;

    @Schema(name = "name", description = "名称")
    @NotBlank(message = "name不能为空")
    private String name;

    @Schema(name = "des", description = "描述")
    private String des;
}
