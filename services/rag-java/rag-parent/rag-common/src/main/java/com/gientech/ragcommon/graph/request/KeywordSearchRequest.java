package com.gientech.ragcommon.graph.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class KeywordSearchRequest {

    @NotNull(message = "图谱不能为空")
    @Schema(name = "spaceName",description = "图空间")
    private String spaceName;

    @NotBlank(message = "节点类型不能为空")
    @Schema(name = "nodeType",description = "节点类型")
    private String nodeType;

    @NotBlank(message = "节点关键字不能为空")
    @Schema(name = "keyword",description = "节点关键字")
    private String keyword;
}
