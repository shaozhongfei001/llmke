package com.gientech.ragcommon.qa.dto;


import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

/**
 * @Descrption:
 * @Author:ws
 * @Date:2024/06/04 09:36
 **/
@Schema(name = "提问内容响应体")
@Data
public class ReplyContentDTO {


    /**
     * 答案内容
     */
    @Schema(name = "content", description = "答案内容")
    private String content;

    /**
     * 类型
     */
    @Schema(name = "markdown", description = "类型")
    private String type = "markdown";

}
