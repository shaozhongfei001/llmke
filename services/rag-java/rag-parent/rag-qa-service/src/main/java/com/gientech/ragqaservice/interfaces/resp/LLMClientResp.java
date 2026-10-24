package com.gientech.ragqaservice.interfaces.resp;

import lombok.Data;

/**
 * @author chenjuan
 * @date 2025/6/24 14:20
 */
@Data
public class LLMClientResp<T> {
    private Integer code;
    private String msg;
    private T data;
}
