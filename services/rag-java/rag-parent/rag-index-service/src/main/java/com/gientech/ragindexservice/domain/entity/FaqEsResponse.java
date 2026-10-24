package com.gientech.ragindexservice.domain.entity;

import lombok.Data;

/**
 * @author chenjuan
 * @date 2025/5/14 10:49
 */
@Data
public class FaqEsResponse {
    private int code;
    private String msg;
    private FaqEsInfo data;
}
