package com.gientech.ragcommon.qa.enmus;

import com.fasterxml.jackson.annotation.JsonValue;
import lombok.Getter;

@Getter
public enum SearchPolicyEnums {
    HYBRID_RETRIEVAL(1,"混合检索"),
    FULL_TEXT_RETRIEVAL(2,"全文检索"),
    NEURAL_RETRIEVAL(3,"语义检索");
    @JsonValue
    private Integer code;
    private String desc;

    SearchPolicyEnums(Integer code, String desc) {
        this.code = code;
        this.desc = desc;
    }
}
