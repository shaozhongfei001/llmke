package com.gientech.ragcommon.auth.dto;

import com.fasterxml.jackson.databind.annotation.JsonSerialize;
import com.fasterxml.jackson.databind.ser.std.ToStringSerializer;
import com.gientech.ragcommon.auth.enums.ResourceTypeEnum;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.util.ArrayList;
import java.util.List;

//@Schema(name = "菜单详情")
@Data
public class MenuDTO {

    @JsonSerialize(using = ToStringSerializer.class)
    //@Schema(name = "id", description = "权限id")
    private Long id;

    //@Schema(name = "name", description = "权限名称")
    private String name;

    //@Schema(name = "url", description = "接口路径")
    private String url;

    //@Schema(name = "icon", description = "图标")
    private String icon;

    @JsonSerialize(using = ToStringSerializer.class)
    //@Schema(name = "pid", description = "父id")
    private Long pid;

    //@Schema(name = "resourceType", description = "1:菜单;2:接口")
    private Integer resourceType;

    //@Schema(name = "permission", description = "是否有权限 true:是;false:否")
    private Boolean permission;

    //@Schema(name = "code", description = "编码")
    private String code;

    //@Schema(name = "subMenuDTOList", description = "子菜单")
    private List<MenuDTO> subMenuDTOList = new ArrayList<>();
}
