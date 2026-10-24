package com.gientech.ragqaservice.domain.entity;


import com.gientech.ragcommon.qa.request.AiRequest;
import lombok.*;

import java.io.Serializable;
import java.util.Date;

@Getter
@Setter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Question implements Serializable {

    private static final long serialVersionUID = 1L;

    /**
     * 主键
     */
    private Long id;

    /**
     * 创建时间
     */
    private Date gmtCreate;

    /**
     * 修改时间
     */
    private Date gmtModified;

    /**
     * 对话id
     */
    private Long dialogueId;

    /**
     * 内容
     */
    private String content;

    /**
     * TEXT：文本；VOICE：语音
     */
    private String type;

    /**
     * 前端生成的uuid
     */
    private String frontUuid;

    /**
     * 模型算法
     */
    private String algModel;

    /**
     * 模型参数
     */
    private String algParams;

    /**
     * 知识库名称
     */
    private String knowledgeBaseName;

    /**
     * 知识库参数
     */
    private String knowledgeParams;

    /**
     * 存的语音地址
     */
    private String audioUrl;


    public void buildQuestion(String modelName, Long dialogueId, AiRequest aiRequest, String algParams) {
        this.setAlgModel(modelName);
        this.setContent(aiRequest.getContent());
        this.setType(aiRequest.getType());
        this.setFrontUuid(aiRequest.getQueryId());
        this.setDialogueId(dialogueId);
        this.setAudioUrl(aiRequest.getAudioUrl());
        this.setAlgParams(algParams);
    }
}
