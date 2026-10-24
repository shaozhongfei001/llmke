package com.gientech.ragcommon.qa.request;

import com.gientech.ragcommon.qa.enmus.SysTypeEnums;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotEmpty;
import lombok.Data;

import java.util.Date;

/**
 * @Descrption:
 * @Author:liutaiyun
 * @Date:2025/01/08 15:35
 **/
@Schema(name = "单文档问答AI请求体")
@Data
public class CommonSearchRequest {

    @Schema(name = "sessionId",description = "会话id", nullable = true)
    @NotEmpty(message="会话id不能为空！")
    private String sessionId;

    @Schema(name = "queryId",description = "提问id", nullable = true)
    @NotEmpty(message="提问id不能为空！")
    private String queryId;

    @Schema(name = "sysType",description = "系统类型(INT_SESSION:智能会话;KNO_INDEX:知识索引;TEMPORARY:临时会话)")
    private SysTypeEnums sysType=SysTypeEnums.KNO_INDEX;

    @Schema(name = "lastDate",description = "提问时间")
    private Date lastDate;

    /**
     * TEXT：文本；VOICE：语音
     */
    @Schema(name = "type",description = "内容类型不能（TEXT：文本；VOICE：语音）", nullable = true)
    @NotEmpty(message="内容类型不能为空！")
    private String type;


    @Schema(name = "content",description = "提问内容", nullable = true)
    @NotEmpty(message="提问内容不能为空！")
    private String content;

    @Schema(name = "configId",description = "检索配置id", nullable = true)
    private Long configId;

}
