package com.gientech.ragcommon.index.response;

import lombok.Data;

/**
 * @author chenjuan
 * @date 2025/5/9 17:11
 */
@Data
public class PyEsResponse<T> {
    private Integer code;
    private String msg;
    private T data;
}
