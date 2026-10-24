package com.gientech.ragauthservice.interfaces.req;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
public class UpdatePasswordByQuestionReq {

    @NotBlank(message = "密钥验证通过的key")
    private String validateKey;

    @NotBlank(message = "密码不能为空")
    private String password;
}
