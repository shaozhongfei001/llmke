package com.gientech.ragcommon.qa.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotEmpty;
import lombok.Data;

import java.util.Date;

/**
 * 新增（或更新）问答内容请求体
 */

@Data
@Schema(name = "新增（或更新）问答内容请求体")
public class QuestionAndAnswerAddReq {
    @Schema(name = "sessionId",description = "会话id", nullable = true)
    @NotEmpty(message="会话id不能为空！")
    private String sessionId;

    @Schema(name = "queryId",description = "提问id", nullable = true)
    @NotEmpty(message="提问id不能为空！")
    private String queryId;

    @Schema(name = "lastDate",description = "提问时间")
    private Date lastDate;

    @Schema(name = "questionContent",description = "提问内容", nullable = true)
    @NotEmpty(message="提问内容不能为空！")
    private String questionContent;

    @Schema(name = "configId",description = "检索配置id", nullable = true)
    private Long configId;

    @Schema(name = "answerContent",description = "回答内容", nullable = true)
    private String answerContent;

    @Schema(name = "algModel",description = "模型算法(不传时默认为检索配置id对应的模型算法)", nullable = true)
    private String algModel;
}
