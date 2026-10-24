package com.gientech.ragindexservice.domain.entity;

import lombok.Data;

import java.io.Serializable;

@Data
public class KnowledgeBaseFile implements Serializable {

    private static final long serialVersionUID = 1L;

    /**
     * 知识库id
     */
    private Long kbId;

    /**
     * 文件总大小  单位:M
     */
    private Double fileTotalSize;

    /**
     * 文件数量
     */
    private Integer fileCount;
}
