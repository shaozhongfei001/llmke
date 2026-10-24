package com.gientech.tools.database.interfaces.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Schema(name = "更新数据表信息")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class UpdateTableInfoReq {

    /** 编号 */
    @Schema(name = "tableId",description = "数据表编号")
    @NotNull(message = "数据表编号不能为空")
    private Long tableId;

    /** 数据库名称 */
    @Schema(name = "businessName",description = "数据表名称")
    @NotNull(message = "数据表名称不能为空")
    private String businessName ;

    /** 数据库描述 */
    @Schema(name = "description",description = "数据表描述")
    @NotNull(message = "数据表描述不能为空")
    private String description ;
}
