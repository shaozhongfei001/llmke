package com.gientech.ragcommon.index.enmus;

import com.fasterxml.jackson.annotation.JsonValue;
import lombok.Getter;

import java.util.Objects;

/**
 * @author: shirleychen
 * @date 2025/12/9 11:35
 * @description
 */
@Getter
public enum RetryTaskEnums {
    FILE(1, "ProcessFileRunnable"),
    CHUNK(2, "ReEmbeddingChunkRunnable"),
    REPARSE(3, "ReParseFileRunnable");

    @JsonValue
    private final Integer code;
    private final String desc;

    RetryTaskEnums(Integer code, String desc) {
        this.code = code;
        this.desc = desc;
    }

    public static RetryTaskEnums of(Integer code) {
        if (Objects.isNull(code)) {
            return null;
        }
        for (RetryTaskEnums retryTaskEnums : RetryTaskEnums.values()) {
            if (retryTaskEnums.getCode().equals(code)) {
                return retryTaskEnums;
            }
        }
        return null;
    }
}
