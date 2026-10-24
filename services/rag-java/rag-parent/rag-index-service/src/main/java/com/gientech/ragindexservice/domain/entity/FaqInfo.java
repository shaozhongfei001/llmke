package com.gientech.ragindexservice.domain.entity;


import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.alibaba.fastjson2.annotation.JSONField;
import lombok.Data;

import java.util.Date;
import java.util.List;


@Data
public class FaqInfo {

    private Long id;

    private Long kbId;

    @JSONField(name = "knowledge_base_name")
    private String knowledgeBaseName;

    /**
     * 问答对id
     */
    @JSONField(name = "pk")
    private Long pk;

    /**
     * 相似问关联的pk
     */
    @JSONField(name = "related_pk")
    private Long relatedPk;

    /**
     * question@@answer
     */
    @JSONField(name = "page_content")
    private String pageContent;

    /**
     * 文件夹id
     */
    @JSONField(name = "folder_id")
    private Long folderId;

    /**
     * 问题
     */
    @JSONField(name = "question")
    private String question;

    /**
     * 答案
     */
    @JSONField(name = "answer")
    private String answer;

    /**
     * 启用状态，0:待启用，1：已启用
     */
    @JSONField(name = "status")
    private Integer status;

    /**
     * 文件路径
     */
    @JSONField(name = "source")
    private String sourceFile;

    /**
     * 文件名
     */
    @JSONField(name = "source")
    private String sourceFileName;

    /**
     * 文档id
     */
    @JSONField(name = "document_id")
    private Long documentId;

    /**
     * faq管理的文件id
     */
    @JSONField(name = "file_id")
    private Long faqFileId;

    /**
     * metadata数据
     */
    private JSONObject metadata;

    /**
     * 1原faq ,2相似问
     */
    @JSONField(name = "faq_type")
    private Integer faqType;

    private Date gmtCreate;

    private Date gmtModified;

    private String updateBy;

    private String createBy;

    private Integer isDel;

    private List<String> labels;
}
