package com.gientech.ragcommon.index.enmus;

import com.fasterxml.jackson.annotation.JsonValue;
import lombok.Getter;

/**
 * @author: shirleychen
 * @date 2025/12/2 19:17
 * @description 1-处理中 2-等待处理 3-处理完成 4-处理失败
 */

@Getter
public enum ReEmbeddingRetryEnums {
    PROCESSING(1,"处理中"),
    WAITING_NEXT(2,"等待下次调度"),
    SUCCEED(3, "最终成功"),
    FAIL(4,"最终失败")
    ;

    @JsonValue
    private final Integer code;
    private final String desc;

    ReEmbeddingRetryEnums(Integer code, String desc) {
        this.code = code;
        this.desc = desc;
    }
}
