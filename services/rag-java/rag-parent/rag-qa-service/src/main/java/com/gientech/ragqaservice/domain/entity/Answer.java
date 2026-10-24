package com.gientech.ragqaservice.domain.entity;

import com.gitee.sunchenbin.mybatis.actable.annotation.Column;
import lombok.*;

import java.io.Serializable;
import java.util.Date;

@Getter
@Setter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Answer implements Serializable {


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
     * 问题id
     */
    private Long questionId;

    /**
     * 召回内容（json）
     */
    private String reference;

    /**
     * 算法评测日志(json)
     */
    private String logResult;

    /**
     * 知识检索召回测试的参数
     */
    private String retrieveRecallParam;

    /**
     * 问题推荐
     */
    private String recommendQuestion;

    /**
     * 推理类型 1:常推理接口, 2:表格推理接口 默认值1
     */
    private Integer llmType;

    /**
     * 响应的类型 1:正常大模型推理; 2:FAQ; 3 命中敏感词;4 强知识依赖;5文档上传问答
     */
    private Integer resultType;

    /**
     * 问答接口响应时间
     */
    private Long respTime;


    private String databaseReference;

}
