package com.gientech.ragauthservice.interfaces.req;

import com.gientech.ragcommon.auth.dto.UserSecurityQuestionDTO;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

import java.util.List;

@Data
public class ValidateSecurityQuestionReq {

    private List<UserSecurityQuestionDTO> userSecurityQuestionList;

    @NotBlank(message = "用户名不能为空")
    private String username;

    @NotBlank(message = "验证码不能为空")
    private String verifyCode;
}
