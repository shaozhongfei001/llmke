package com.gientech.ragcommon.auth.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import lombok.Data;

import java.util.List;

//@Schema(name = "新增用户请求",requiredProperties = {"userName"})
@Data
public class AddUserReq {

    //@Schema(name = "userName",description = "用户名")
    @NotBlank(message = "用户名不能为空")
    private String userName;

    //@Schema(name = "userRealname",description = "用户真实姓名")
    @NotBlank(message = "用户真实姓名不能为空")
    private String userRealname;

    //@Schema(name = "userPhone",description = "手机号")
    @NotBlank(message = "手机号不能为空")
    @Pattern(regexp = "^((13[0-9])|(14[5-9])|(15([0-3]|[5-9]))|(16[6-7])|(17[1-8])|(18[0-9])|(19[1|3])|(19[5|6])|(19[8|9]))\\d{8}$", message = "必须是正确的国内手机号")
    private String userPhone;

    //@Schema(name = "userEmail",description = "邮件地址")
    @NotBlank(message = "邮件不能为空")
    @Pattern(regexp = "\\w+([-+.]\\w+)*@\\w+([-.]\\w+)*\\.\\w+([-.]\\w+)*", message = "必须是正确的邮件地址")
    private String userEmail;

    //@Schema(name = "deptId",description = "部门id")
    private String deptId;

    //@Schema(name = "deptName",description = "部门名称")
    private String deptName;

    @NotEmpty(message = "roleIds不能为空")
    private List<Long> roleIds;

    //@Schema(name = "systemSource",description = "用户来源")
    private Integer systemSource;

}
