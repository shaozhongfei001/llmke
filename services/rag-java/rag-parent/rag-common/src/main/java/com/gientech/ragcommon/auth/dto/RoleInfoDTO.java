package com.gientech.ragcommon.auth.dto;

import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.databind.annotation.JsonSerialize;
import com.fasterxml.jackson.databind.ser.std.ToStringSerializer;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import java.util.Date;

@Schema(name = "角色详情")
@Data
public class RoleInfoDTO {

    @Schema(name = "createBy",description = "创建人")
    private String createBy;

    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss",timezone = "GMT+8")
    @Schema(name = "gmtCreate",description = "创建时间")
    private Date gmtCreate;

    @Schema(name = "updateBy",description = "更新人")
    private String updateBy;

    @Schema(name = "gmtModified",description = "更新时间")
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss",timezone = "GMT+8")
    private Date gmtModified;

    @JsonSerialize(using = ToStringSerializer.class)
    @Schema(name = "id",description = "角色id")
    private Long id;

    @Schema(name = "name",description = "角色名称")
    private String name;

    @Schema(name = "description",description = "描述")
    private String description;

    @Schema(name = "status",description = "状态 0 禁用 1 启用")
    private Integer status;

    @Schema(name = "roleType",description = "角色类型 1超级管理员 2 管理员  null 其他")
    private Integer roleType;
}
