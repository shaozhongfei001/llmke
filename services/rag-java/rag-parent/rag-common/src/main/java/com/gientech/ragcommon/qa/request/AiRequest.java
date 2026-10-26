package com.gientech.ragcommon.qa.request;


import com.gientech.ragcommon.qa.enmus.SysTypeEnums;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotEmpty;
import lombok.Data;

import java.util.Date;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.atomic.AtomicReference;

/**
 * @Description:
 * @Author: ws
 * @Date: 2024/6/3 11:17
 */
@Schema(name = "AI请求体")
@Data
public class AiRequest {

    @Schema(name = "sessionId",description = "会话id", nullable = true)
    @NotEmpty(message="会话id不能为空！")
    private String sessionId;

    @Schema(name = "queryId",description = "提问id", nullable = true)
    @NotEmpty(message="提问id不能为空！")
    private String queryId;

    @Schema(name = "sysType",description = "系统类型(INT_SESSION:智能会话;KNO_INDEX:知识索引;TEMPORARY:临时会话  RETRIEVE_RECALL_TEST:知识检索召回测试")
    private SysTypeEnums sysType = SysTypeEnums.KNO_INDEX;

    @Schema(name = "lastDate",description = "提问时间")
    private Date lastDate;

    @Schema(name = "audioUrl",description = "存的语音地址")
    private String audioUrl;

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

    @Schema(name = "fileUids",description = "文件uid,文档上传问答使用")
    private List<String> fileUids;

    @Schema(name = "config",description = "检索召回配置信息(前端组装成josn格式的数据类型)")
    private String config;

    @Schema(name = "enableThinking",description = "qwen3相关模型的功能 true:开启推理检索,false关闭推理检索")
    private Boolean enableThinking = false;

    @Schema(name = "enableWebsearch",description = "是否启用联网检索，默认值false")
    private Boolean enableWebsearch = Boolean.FALSE;

    /**
     * R13-GRAPH-12：GraphRAG 全局模式开关（社区摘要 map-reduce）。
     * 放在请求上而不是只靠助手配置 JSON —— 配置在写入对话时会被规范化，
     * 自定义字段（query_mode）会被丢掉，导致"以为走了 GraphRAG，实际还是普通召回"。
     */
    @com.fasterxml.jackson.annotation.JsonProperty("globalMode")
    private Boolean globalMode = Boolean.FALSE;

    private Long dialogueId;
}
