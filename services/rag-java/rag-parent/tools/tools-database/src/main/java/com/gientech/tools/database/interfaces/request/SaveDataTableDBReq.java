package com.gientech.tools.database.interfaces.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Schema(name = "保存数据库信息-数据表")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SaveDataTableDBReq {

    /** 编号 */
    @Schema(name = "id",description = "编号")
    private Long id;

    /** 数据库名称 */
    @Schema(name = "name",description = "数据库名称")
    @NotNull(message = "数据库名称不能为空")
    private String name ;

    /** 数据库描述 */
    @Schema(name = "description",description = "数据库描述")
    private String description ;
}
