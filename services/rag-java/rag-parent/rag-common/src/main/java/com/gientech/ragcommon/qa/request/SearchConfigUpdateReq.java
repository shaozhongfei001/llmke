package com.gientech.ragcommon.qa.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.util.ArrayList;
import java.util.List;

@Schema(name = "更新查询配置请求参数",requiredProperties = {"id"})
@Data
public class SearchConfigUpdateReq {

    @Schema(name = "id", description = "主键")
    @NotNull(message = "id不能为空")
    private Long id;

    @Schema(name = "configJson", description = "配置详情")
    private String configJson;

    @Schema(name = "sensitiveWordIds", description = "敏感词ids")
    private String sensitiveWordIds;

    @Schema(name = "defaultAnswer", description = "默认回答(sensitive_word_ids不为空时,必填)")
    private String defaultAnswer;

    @Schema(name = "name", description = "名称")
    private String name;

    @Schema(name = "des", description = "描述")
    private String des;

    @Schema(name = "isDefault", description = "是否默认 0:否；1:是 ")
    private Integer isDefault = 0;

    @Schema(name = "enabledFaq", description = "是否开启faq(0:否;1:是)")
    private Integer enabledFaq = 0;

    @Schema(name = "dependOnKb", description = "是否强依赖知识库(0:否;1:是)")
    private Integer dependOnKb = 0;
}
