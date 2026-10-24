package com.gientech.tools.database.interfaces.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Schema(name = "保存数据库信息-直连数据库")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SaveDirectDBReq {

    /** 编号 */
    @Schema(name = "id",description = "编号")
    private Long id;

    /** 数据库名称 */
    @Schema(name = "name",description = "数据库名称")
    private String name ;

    /** 数据库描述 */
    @Schema(name = "description",description = "数据库描述")
    private String description ;

    /** 数据库类型;MySQL,SQLServer,Doris */
    @Schema(name = "dbType",description = "数据库类型;MySQL,SQLServer,Doris")
    private String dbType ;

    /** 连接地址 */
    @Schema(name = "dbHost",description = "连接地址")
    private String dbHost ;

    /** 连接端口 */
    @Schema(name = "dbPort",description = "连接端口")
    private Integer dbPort ;

    /** 数据库名称 */
    @Schema(name = "dbDatabase",description = "数据库名称")
    private String dbDatabase ;

    /** 连接用户 */
    @Schema(name = "dbUser",description = "连接用户")
    private String dbUser ;

    /** 连接密码 */
    @Schema(name = "dbPassword",description = "连接密码")
    private String dbPassword ;
}
