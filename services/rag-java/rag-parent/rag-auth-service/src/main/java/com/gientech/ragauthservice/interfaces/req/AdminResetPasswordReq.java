package com.gientech.ragauthservice.interfaces.req;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class AdminResetPasswordReq {

    @NotBlank(message = "用户id")
    private Long userId;

    @NotBlank(message = "新密码不能为空")
    private String password;


    @NotBlank(message = "验证码不能为空")
    private String verifyCode;

}
