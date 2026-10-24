package com.gientech.start.storage.properties;

import lombok.Data;

/** 单个存储配置（R12 兼容实现）。 */
@Data
public class Properties {

    /** 对外可访问端点，例如 http://127.0.0.1:19000（无尾斜杠） */
    private String endPoint;

    /** 桶名 */
    private String bucketName;

    private String accessKey;

    private String secretKey;

    /** 平台标识（rag-qa / rag-index 等），为空表示共享 */
    private String platform;

    /** 历史字段：对外域名前缀，未配置时回落 endPoint */
    private String domain;

    public String getDomain() {
        return (domain == null || domain.isBlank()) ? endPoint : domain;
    }
}
