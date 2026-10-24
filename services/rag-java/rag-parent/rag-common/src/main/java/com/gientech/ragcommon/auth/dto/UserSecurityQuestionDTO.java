package com.gientech.ragcommon.auth.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Schema(name = "user_security_question")
@Data
public class UserSecurityQuestionDTO {

    @Schema(name = "id",description = "主键编号")
    private Long id;

    @Schema(name = "userId",description = "用户编号")
    private Long userId;

    @Schema(name = "question",description = "问题")
    private String question;

    @Schema(name = "answer",description = "答案")
    private String answer;

}
