package com.gientech.ragauthservice.interfaces.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import com.fasterxml.jackson.annotation.JsonFormat;
import java.util.Date;
import java.math.BigDecimal;

@Schema(name = "")
@Data
public class RoleResourceDTO {

    @Schema(name = "isDtl",description = "逻辑删除 是否删除 1是 0否")
    private String isDtl;

    @Schema(name = "createBy",description = "创建人")
    private String createBy;

    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss",timezone = "GMT+8")
    @Schema(name = "gmtCreate",description = "创建时间")
    private Date gmtCreate;

    @Schema(name = "updateBy",description = "更新人")
    private String updateBy;

    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss",timezone = "GMT+8")
    @Schema(name = "gmtModified",description = "更新时间")
    private Date gmtModified;

    @Schema(name = "id",description = "主键")
    private Long id;

    @Schema(name = "roleId",description = "角色id")
    private Long roleId;

    @Schema(name = "resourceId",description = "资源id")
    private Long resourceId;

    @Schema(name = "status",description = "状态（1:启用; 0:禁用）")
    private Integer status;

}
