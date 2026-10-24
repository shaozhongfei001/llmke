package com.gientech.ragcommon.qa.request;

import cn.hutool.core.util.StrUtil;
import com.gientech.ragcommon.qa.enmus.SysTypeEnums;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotEmpty;
import lombok.Data;
import org.apache.commons.lang3.StringUtils;

import java.util.Date;
import java.util.List;

/**
 * @Descrption:
 * @Author:liutaiyun
 * @Date:2025/01/06 16:52
 **/

@Schema(name = "单文档问答AI请求体")
@Data
public class AiRequestForSingleDocument {

    @Schema(name = "sessionId", description = "会话id", nullable = true)
    @NotEmpty(message = "会话id不能为空！")
    private String sessionId;

    @Schema(name = "queryId", description = "提问id", nullable = true)
    @NotEmpty(message = "提问id不能为空！")
    private String queryId;

    @Schema(name = "sysType", description = "系统类型(INT_SESSION:智能会话;KNO_INDEX:知识索引;TEMPORARY:临时会话)")
    private SysTypeEnums sysType = SysTypeEnums.KNO_INDEX;

    @Schema(name = "lastDate", description = "提问时间")
    private Date lastDate;

    @Schema(name = "audioUrl", description = "存的语音地址")
    private String audioUrl;

    /**
     * TEXT：文本；VOICE：语音
     */
    @Schema(name = "type", description = "内容类型不能（TEXT：文本；VOICE：语音）", nullable = true)
    @NotEmpty(message = "内容类型不能为空！")
    private String type;


    @Schema(name = "content", description = "提问内容", nullable = true)
    @NotEmpty(message = "提问内容不能为空！")
    private String content;

    @Schema(name = "configId", description = "检索配置id")
    private Long configId;

    @Schema(name = "newConfigId", description = "新检索配置id")
    private Long newConfigId;

    @Schema(name = "fileUrl", description = "原文件url", nullable = true)
    private String fileUrl;

    @Schema(name = "enableThinking",description = "qwen3相关模型的功能 true:开启推理检索,false关闭推理检索")
    private Boolean enableThinking = false;

    @Schema(name = "qaHistory", description = "对话历史", nullable = true)
    private List<qaPair> qaHistory;

    public String getDocumentTitle() {
        if (StringUtils.isNotEmpty(fileUrl))
            return fileUrl.substring(fileUrl.lastIndexOf("/") + 1);
        return null;
    }

    @Data
    public static class qaPair {
        private String query;
        private String answer;
    }

}
