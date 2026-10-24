package com.gientech.ragindexservice.application.remote.response;

import lombok.Data;

/**
 * @author: shirleychen
 * @date 2025/12/2 19:56
 * @description
 */
@Data
public class PyMilvusResponse<T> {
    private Integer code;
    private String msg;
    private T data;
}
