package com.gientech.ragcommon.graph.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.util.List;

@Schema(name = "点以及点的属性")
@Data
public class NodeDTO {

    @Schema(name = "nodeType",description = "点的名称")
    private String nodeType;

    @Schema(name = "properties",description = "点属性")
    private List<NodeProperty> properties;

    @Schema(name = "点的属性")
    @Data
    public static class NodeProperty{

        @Schema(name = "propertyName",description = "属性名称")
        private String propertyName;

        @Schema(name = "propertyType",description = "属性字段类型")
        private String propertyType;
    }
}
