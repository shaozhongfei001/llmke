package com.gientech.elasticsearchservice.document;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

/**
 * @Description:
 * @Author: chenjuan
 * @Date: 2024/9/23 16:07
 */
@Data
public class MetaData {

    private static final DateTimeFormatter formatter = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    @JsonProperty("chunk_doc_id")
    private String chunkDocId;

    private String offset;

    private String answer;

    @JsonProperty("knowledge_base_name")
    private String knowledgeBaseName;

    @JsonProperty("title_path")
    private String titlePath;

    @JsonProperty("title_tks")
    private String titleTks;

    private String score;

    @JsonProperty("document_id")
    private String documentId;

    private String type;

    private String source;

    @JsonProperty("docnm_kwd")
    private String docnmKwd;

    @JsonProperty("file_path")
    private String filePath;

    @JsonProperty("file_size")
    private String fileSize;

    private String pk;

    @JsonProperty("create_time")
    private String createTime;

    @JsonProperty("update_time")
    private String updateTime;

    @JsonProperty("order_num")
    private String orderNum;

    public void init() {
        LocalDateTime now = LocalDateTime.now();
        this.createTime = now.format(formatter);
        this.updateTime = now.format(formatter);
    }

}
