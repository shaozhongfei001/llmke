package com.gientech.ragcommon.index.dto.tools;

import com.alibaba.fastjson2.annotation.JSONField;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Schema(name = "表字段")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TLTableColumnDto {

    /** 编号 */
    @Schema(name = "id",description = "编号")
    @JSONField(name = "id")
    private Long id;

    /** 业务列名 */
    @Schema(name = "businessName",description = "业务列名(中文)")
    @JSONField(name = "business_name")
    private String businessName ;

    /** 物理列名 */
    @Schema(name = "physicalName",description = "物理列名(英文)")
    @JSONField(name = "physical_name")
    private String physicalName ;

    @Schema(name = "description", description = "列描述")
    @JSONField(name = "description")
    private String description ;

    /** 数据类型 */
    @Schema(name = "dataType",description = "数据类型")
    @JSONField(name = "data_type")
    private String dataType;

    /** 示例数据 */
    @Schema(name = "sampleValues",description = "示例数据")
    @JSONField(name = "sample_values")
    private List<String> sampleValues;
}
