package com.gientech.ragcommon.auth.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

/**
 * 登录请求
 */
//@Schema(name = "登录请求",requiredProperties={"userName","password","verifyCode"})
@Data
public class LoginReq {

    //@Schema(name = "userName",description = "用户名")
    @NotBlank(message = "用户名不能为空")
    private String userName;

    //@Schema(name = "password",description = "密码")
    @NotBlank(message = "密码不能为空")
    private String password;

    //@Schema(name = "verifyCode",description = "验证码")
    @NotBlank(message = "验证码不能为空")
    private String verifyCode;
}
