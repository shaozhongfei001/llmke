package com.gientech.ragcommon.index.dto.tools;

import com.fasterxml.jackson.annotation.JsonFormat;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Date;
import java.util.Objects;

import static com.gientech.ragcommon.qa.constant.AIConstant.DB_PREFIX;

/**
 * @author xiaominzuo
 */
@Schema(name = "数据库")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class TLDatabaseDTO {

    /**
     * 编号
     */
    @Schema(name = "id", description = "编号")
    private Long id;

    /**
     * 数据库名称
     */
    @Schema(name = "name", description = "数据库名称")
    @NotNull(message = "数据库名称不能为空")
    private String name;

    private String primitiveName;

    /**
     * 数据库描述
     */
    @Schema(name = "description", description = "数据库描述")
    @NotNull(message = "数据库描述不能为空")
    private String description;

    /**
     * 数据源类型;DataTable数据表;DirectDB数据库直连;
     */
    @Schema(name = "datasourceType", description = "数据源类型;DataTable数据表;DirectDB数据库直连;")
    @NotNull(message = "数据源类型不能为空")
    private String datasourceType;

    /**
     * 数据库类型;MySQL,SQLServer,Doris
     */
    @Schema(name = "dbType", description = "数据库类型;MySQL,SQLServer,Doris")
    private String dbType;

    /**
     * 连接地址
     */
    @Schema(name = "dbHost", description = "连接地址")
    private String dbHost;

    /**
     * 连接端口
     */
    @Schema(name = "dbPort", description = "连接端口")
    private Integer dbPort;

    /**
     * 数据库名称
     */
    @Schema(name = "dbDatabase", description = "数据库名称")
    private String dbDatabase;

    /**
     * 连接用户
     */
    @Schema(name = "dbUser", description = "连接用户")
    private String dbUser;

    /**
     * 连接密码
     */
    @Schema(name = "dbPassword", description = "连接密码")
    private String dbPassword;

    @Schema(name = "permission", description = "数据权限 0:无任何权限, 1: 读权限，2: 读写权限, 3: 所有权限")
    private Integer permission = 3;

    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss", timezone = "GMT+8")
    @Schema(name = "gmtCreate", description = "创建时间")
    private Date gmtCreate;

    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss", timezone = "GMT+8")
    @Schema(name = "gmtModified", description = "更新时间")
    private Date gmtModified;

    @Schema(name = "createBy", description = "创建人")
    private String createBy;

    @Schema(name = "updateBy", description = "更新人")
    private String updateBy;

    private String generateDescriptionStatus;

    private String genDescriptionErrMsg;

    private Boolean isGenDescription;

    private String tableName4Retrieve;


    @Override
    public boolean equals(Object o) {
        if (o == null || getClass() != o.getClass()) return false;
        TLDatabaseDTO that = (TLDatabaseDTO) o;
        return Objects.equals(id, that.id) && Objects.equals(name, that.name) && Objects.equals(description, that.description) && Objects.equals(datasourceType, that.datasourceType) && Objects.equals(dbType, that.dbType) && Objects.equals(dbHost, that.dbHost) && Objects.equals(dbPort, that.dbPort) && Objects.equals(dbDatabase, that.dbDatabase) && Objects.equals(dbUser, that.dbUser) && Objects.equals(dbPassword, that.dbPassword) && Objects.equals(permission, that.permission) && Objects.equals(gmtCreate, that.gmtCreate) && Objects.equals(gmtModified, that.gmtModified) && Objects.equals(createBy, that.createBy) && Objects.equals(updateBy, that.updateBy);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, name, description, datasourceType, dbType, dbHost, dbPort, dbDatabase, dbUser, dbPassword, permission, gmtCreate, gmtModified, createBy, updateBy);
    }

    public String getPrimitiveName() {
        return DB_PREFIX + this.id;
    }
}
