package com.gientech.ragauthservice.interfaces.req;

import com.gientech.ragcommon.auth.dto.UserSecurityQuestionDTO;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

import java.util.List;

@Schema(name = "保存密保问题")
@Data
public class SaveSecurityQuestionReq {
    private List<UserSecurityQuestionDTO> userSecurityQuestionList;

    @NotBlank(message = "验证码不能为空")
    private String verifyCode;

 }
