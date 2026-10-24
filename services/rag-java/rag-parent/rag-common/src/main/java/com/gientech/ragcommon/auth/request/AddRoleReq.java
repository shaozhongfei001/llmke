package com.gientech.ragcommon.auth.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import lombok.Data;

import java.util.List;

//@Schema(name = "添加角色请求参数",requiredProperties = {"name"})
@Data
public class AddRoleReq {

    //@Schema(name = "name",description = "角色名称")
    @NotBlank(message = "角色名称不能为空")
    private String name;

    //@Schema(name = "description",description = "描述")
    private String description;

    //@Schema(name = "resourceIds",description = "角色权限")
    @NotEmpty(message = "resourceIds不能为空")
    private List<Long> resourceIds;
}
