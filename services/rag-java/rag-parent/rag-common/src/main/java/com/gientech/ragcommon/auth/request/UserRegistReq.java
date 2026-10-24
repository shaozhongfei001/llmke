package com.gientech.ragcommon.auth.request;
import com.gientech.ragcommon.auth.dto.UserSecurityQuestionDTO;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import lombok.Data;

import java.util.List;

//@Schema(name = "用户注册请求",requiredProperties = {"userName","userRealname","userIphone","userEmail","password","passwordAffirm","verifyCode"})
@Data
public class UserRegistReq {

    //@Schema(name = "userName",description = "用户名")
    @NotBlank(message = "用户名不能为空")
    private String userName;

    //@Schema(name = "userRealname",description = "真实姓名")
    @NotBlank(message = "真实姓名不能为空")
    private String userRealname;

    //@Schema(name = "userIphone",description = "手机号")
    @NotBlank(message = "手机号不能为空")
    @Pattern(regexp = "^((13[0-9])|(14[5-9])|(15([0-3]|[5-9]))|(16[6-7])|(17[1-8])|(18[0-9])|(19[1|3])|(19[5|6])|(19[8|9]))\\d{8}$", message = "必须是正确的国内手机号")
    private String userIphone;

    //@Schema(name = "userEmail",description = "邮件地址")
    @NotBlank(message = "邮件地址不能为空")
    @Pattern(regexp = "\\w+([-+.]\\w+)*@\\w+([-.]\\w+)*\\.\\w+([-.]\\w+)*", message = "必须是正确的邮件地址")
    private String userEmail;

    //@Schema(name = "password",description = "密码")
    @NotBlank(message = "密码不能为空")
    private String password;

    //@Schema(name = "passwordAffirm",description = "密码二次确认")
    @NotBlank(message = "确认密码不能为空")
    private String passwordAffirm;

    //@Schema(name = "verifyCode",description = "验证码")
    @NotNull(message = "验证码不能为空")
    private String verifyCode;

    //@Schema(name = "deptId",description = "部门id")
    private String deptId;

    //@Schema(name = "deptName",description = "部门名称")
    private String deptName;

    /**
     * 密保设置
     */
    private List<UserSecurityQuestionDTO> userSecurityQuestionList;


}
