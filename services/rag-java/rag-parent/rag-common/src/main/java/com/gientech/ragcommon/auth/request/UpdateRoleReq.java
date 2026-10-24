package com.gientech.ragcommon.auth.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.util.List;

//@Schema(name = "更新角色请求参数",requiredProperties = {"name","status","resourceIds"})
@Data
public class UpdateRoleReq {

    //@Schema(name = "id",description = "角色id")
    @NotNull(message = "角色id不能为空")
    private Long id;

    //@Schema(name = "name",description = "角色名称")
    @NotBlank(message = "角色名称不能为空")
    private String name;

    //@Schema(name = "description",description = "描述")
    private String description;

    //@Schema(name = "name",description = "态 0 禁用 1 启用")
    @NotNull(message = "状态不能为空")
    private Integer status;

    //@Schema(name = "resourceIds",description = "权限")
    private List<Long> resourceIds;
}
