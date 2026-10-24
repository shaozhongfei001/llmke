package com.gientech.ragcommon.auth.request;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class ForceUpdatePasswordReq {

    @NotBlank(message = "旧密码不能为空")
    private String oldPassword;


    @NotBlank(message = "新密码不能为空")
    private String newPassword;

    @NotBlank(message = "验证码不能为空")
    private String verifyCode;
}
