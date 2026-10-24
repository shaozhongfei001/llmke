package com.gientech.ragcommon.auth.request;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import lombok.Data;
import org.w3c.dom.stylesheets.LinkStyle;

import java.util.List;

@Data
public class UpdateUserReq {

    @NotNull(message = "用户id不能为空")
    private Long id;

    @NotBlank(message = "用户真实名不能为空")
    private String userRealname;

//    @NotBlank(message = "密码不能为空")
//    private String userPassword;

    @NotBlank(message = "手机号码")
    @Pattern(regexp = "^((13[0-9])|(14[5-9])|(15([0-3]|[5-9]))|(16[6-7])|(17[1-8])|(18[0-9])|(19[1|3])|(19[5|6])|(19[8|9]))\\d{8}$", message = "必须是正确的国内手机号")
    private String userPhone;

    @NotBlank(message = "邮箱不能为空")
    @Pattern(regexp = "\\w+([-+.]\\w+)*@\\w+([-.]\\w+)*\\.\\w+([-.]\\w+)*", message = "必须是正确的邮件地址")
    private String userEmail;

    //状态  1启用 0禁用
    @NotNull(message = "状态不能为空")
    private Integer status;

    @NotEmpty(message = "角色不能为空")
    private List<Long> roleIds;

    @NotNull(message = "部门id")
    private Long deptId;

    @NotBlank(message = "部门名称不能为空")
    private String deptName;
}
