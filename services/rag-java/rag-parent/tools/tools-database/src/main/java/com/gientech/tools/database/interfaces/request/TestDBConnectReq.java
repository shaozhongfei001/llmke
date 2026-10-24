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
public class TestDBConnectReq {

    /** 数据库类型;MySQL,SQLServer,Doris */
    @Schema(name = "dbType",description = "数据库类型;MySQL,SQLServer,Doris")
    @NotNull(message = "数据库类型不能为空")
    private String dbType ;

    /** 连接地址 */
    @Schema(name = "dbHost",description = "连接地址")
    @NotNull(message = "连接地址不能为空")
    private String dbHost ;

    /** 连接端口 */
    @Schema(name = "dbPort",description = "连接端口")
    @NotNull(message = "连接端口不能为空")
    private Integer dbPort ;

    /** 数据库名称 */
    @Schema(name = "dbDatabase",description = "数据库名称")
    @NotNull(message = "数据库名称不能为空")
    private String dbDatabase ;

    /** 连接用户 */
    @Schema(name = "dbUser",description = "连接用户")
    @NotNull(message = "连接用户不能为空")
    private String dbUser ;

    /** 连接密码 */
    @Schema(name = "dbPassword",description = "连接密码")
    @NotNull(message = "连接密码不能为空")
    private String dbPassword ;
}
