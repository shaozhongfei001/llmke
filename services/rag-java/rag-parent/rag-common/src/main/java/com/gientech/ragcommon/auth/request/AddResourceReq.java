package com.gientech.ragcommon.auth.request;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;


//@Schema(name = "添加资源请求接口",requiredProperties = {"name","url","pid","seq","resourceType"})
@Data
public class AddResourceReq {

    //@Schema(name = "name",description = "资源名称")
    @NotBlank(message = "name不能为空")
    private String name;

    //@Schema(name = "url",description = "接口路径")
    @NotBlank(message = "name不能为空")
    private String url;

    //@Schema(name = "description",description = "描述")
    private String description;

    //@Schema(name = "icon",description = "图标")
    private String icon;

    //@Schema(name = "pid",description = "父id")
    private Long pid;

    //@Schema(name = "seq",description = "排序")
    @NotNull(message = "seq不能为空")
    private Long seq;

    //@Schema(name = "resourceType",description = "菜单类型 1:菜单;2:接口")
    @NotNull(message = "resourceType不能为空")
    private Integer resourceType;
}
