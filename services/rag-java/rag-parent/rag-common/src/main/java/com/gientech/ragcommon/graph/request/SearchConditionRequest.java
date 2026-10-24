package com.gientech.ragcommon.graph.request;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.*;

/**
 * @Descrption: 查询条件入参对象
 * @Author:liutaiyun
 * @Date:2023/02/14 15:57
 **/
@Getter
@Setter
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(name = "图查询条件")
public class SearchConditionRequest {

    @Schema(name = "propertyKey",description = "属性KEY")
    private String propertyKey;

    @Schema(name = "operator",description = "操作符")
    private String operator;

    @Schema(name = "propertyValue",description = "属性值")
    private String propertyValue;

    @Schema(name = "logicalOperator",description = "逻辑操作符号")
    private String logicalOperator;

    @Schema(name = "propertyName",description = "用于路径查询")
    private String propertyName;

    @Schema(name = "propertyType",description = "属性类型")
    private String propertyType;
}

