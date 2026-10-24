package com.gientech.ragcommon.auth.request;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class SimpleLoginReq {

    //@Schema(name = "userName",description = "用户名")
    @NotBlank(message = "用户名不能为空")
    private String userName;

    //@Schema(name = "password",description = "密码")
    @NotBlank(message = "密码不能为空")
    private String password;

    public LoginReq adaptToLoginReq() {
        LoginReq loginReq = new LoginReq();
        loginReq.setUserName(userName);
        loginReq.setPassword(password);
        return loginReq;
    }
}
