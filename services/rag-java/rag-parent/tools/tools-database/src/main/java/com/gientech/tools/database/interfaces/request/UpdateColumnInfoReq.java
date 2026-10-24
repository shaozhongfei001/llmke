package com.gientech.tools.database.interfaces.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Schema(name = "更新字段信息")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class UpdateColumnInfoReq {

    /** 字段编号 */
    @Schema(name = "columnId",description = "字段编号")
    @NotNull(message = "字段编号不能为空")
    private Long columnId;

    /** 字段描述 */
    @Schema(name = "description",description = "字段描述")
    @NotNull(message = "字段描述不能为空")
    private String description ;


    /** 字段描述 */
    @Schema(name = "dataType",description = "数据类型")
    @NotNull(message = "数据类型不能为空")
    private String dataType ;
}
