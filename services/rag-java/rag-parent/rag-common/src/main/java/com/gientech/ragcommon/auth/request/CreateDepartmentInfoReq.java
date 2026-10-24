package com.gientech.ragcommon.auth.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Schema(name = "创建请求参数")
@Data
public class CreateDepartmentInfoReq {

    @Schema(name = "name",description = "部门名称")
    @NotBlank(message = "部门名称不能为空")
    private String name;

    @Schema(name = "code",description = "部门编码")
    private String code;

    @Schema(name = "admin",description = "部门管理员")
    private String admin;

    @Schema(name = "parentId",description = "上级部门ID")
    private Long parentId;

}
