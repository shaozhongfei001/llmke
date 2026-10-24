package com.gientech.ragcommon.graph.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.util.List;

@Schema(name = "边以及边的属性")
@Data
public class EdgeDTO {

    @Schema(name = "edgeType",description = "边的名称")
    private String edgeType;

    @Schema(name = "properties",description = "边属性")
    private List<EdgeProperty> properties;

    @Schema(name = "边的属性")
    @Data
    public static class EdgeProperty{

        @Schema(name = "propertyName",description = "属性名称")
        private String propertyName;

        @Schema(name = "propertyType",description = "属性字段类型")
        private String propertyType;
    }
}
