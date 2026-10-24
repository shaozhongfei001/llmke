package com.gientech.ragcommon.index.enmus;

import com.fasterxml.jackson.annotation.JsonValue;
import lombok.Getter;

/**
 * @author: shirleychen
 * @date 2025/11/28 11:05
 * @description
 */
@Getter
public enum ReEmbeddingTaskEnums {
    WAIT_TO_START(0, "未开始"),
    PARSING(1, "解析中"),
    PARSED_SUCCESS(2, "解析完成"),
    PARSED_FAIL(3, "解析失败"),
    PROCESSED(4, "已处理结果未知");


    @JsonValue
    private final Integer code;
    private final String desc;

    ReEmbeddingTaskEnums(Integer code, String desc) {
        this.code = code;
        this.desc = desc;
    }
}
