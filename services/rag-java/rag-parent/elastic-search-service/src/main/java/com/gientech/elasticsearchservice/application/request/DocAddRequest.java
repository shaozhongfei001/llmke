package com.gientech.elasticsearchservice.application.request;

import lombok.Data;

/**
 * @Description:
 * @Author: chenjuan
 * @Date: 2024/9/20 17:04
 */
@Data
public class DocAddRequest<T> {
    private String indexName;

    private String docId;

    private T doc;
}
