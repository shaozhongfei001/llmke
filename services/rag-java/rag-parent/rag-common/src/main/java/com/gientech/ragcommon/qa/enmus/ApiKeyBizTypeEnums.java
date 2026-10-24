package com.gientech.ragcommon.qa.enmus;

import lombok.Getter;

@Getter
public enum ApiKeyBizTypeEnums {

    QA_HELPER(1, "问答助手"),;

    private Integer code;
    private String desc;

    ApiKeyBizTypeEnums(Integer code, String desc) {
        this.code = code;
        this.desc = desc;
    }
}
