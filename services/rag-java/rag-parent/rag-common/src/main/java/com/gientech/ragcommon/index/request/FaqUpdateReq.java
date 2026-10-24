package com.gientech.ragcommon.index.request;

import com.alibaba.fastjson.annotation.JSONField;
import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONObject;
import lombok.Data;

import java.util.List;
import java.util.Set;

@Data
public class FaqUpdateReq {

    @JSONField(name = "source")
    private String source;

    @JSONField(name = "knowledge_base_name")
    private String knowledgeBaseName;

    @JSONField(name = "page_content")
    private String pageContent;

    @JSONField(name = "pk")
    private Long pk;

    @JSONField(name = "related_pk")
    private Long relatedPk;

    @JSONField(name = "question")
    private String question;

    @JSONField(name = "answer")
    private String answer;

    @JSONField(name = "folder_id")
    private Long folderId;

    @JSONField(name = "faq_type")
    private Integer faqType;

    @JSONField(name = "status")
    private Integer status;

    @JSONField(name = "file_id")
    private String faqFileId;

    @JSONField(name = "document_id")
    private String FileId;

    @JSONField(name = "labels")
    private Set<String> labels;
}
