package com.gientech.ragcommon.qa.dto;

import com.gientech.ragcommon.qa.enmus.ReplyStatusEnums;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Getter;
import lombok.Setter;

import java.util.Date;

/**
 * @Descrption:
 * @Author:ws
 * @Date:2024/06/04 09:36
 **/
@Schema(name = "参考链接响应体")
@Setter
@Getter
public class KnowledgeDTO {

    @Schema(name = "sessionId",description = "会话id")
    private String sessionId;

    /**
     * 问题ID
     */
    @Schema(name = "queryId",description = "提问id")
    private String queryId;

    /**
     * 问题提交时间
     */
    @Schema(name = "lastDate",description = "参考链接提交时间")
    private Date lastDate;

    /**
     * 1.进行中，2.结束，3.异常
     */
    @Schema(name = "status",description = "答案类型体：1.进行中，2.结束，3.异常")
    private ReplyStatusEnums status;

    /**
     * 答案内容
     */
    @Schema(name = "content",description = "答案内容")
    private String content;

    @Schema(name = "filePath",description = "文件地址")
    private String filePath;

}
