package com.gientech.ragcommon.qa.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

/**
 * @Descrption: 问答对
 * @Author:liutaiyun
 * @Date:2024/05/13 15:07
 **/
@Data
public class QueryReplyPairDTO {

    /**
     * 问题
     */
    @Schema(name = "query",description = "问题")
    private QuestionDTO query;

    /**
     * 答案
     */
    @Schema(name = "reply",description = "答案")
    private AnswerDTO reply;
}
