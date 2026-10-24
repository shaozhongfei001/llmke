package com.gientech.ragcommon.qa.enmus;

import com.fasterxml.jackson.annotation.JsonValue;

public enum AIResultTypeEnum {

    LLM(1,"正常大模型推理"),
    FAQ(2,"FAQ"),
    SENSITIVE_WORDS(3,"命中敏感词"),
    DEPEND_ON_KB(4,"强知识依赖"),
    FILE_UPLOAD(5,"文档上传问答"),
    LLM_TABLE(6,"表格问答"),
    ;

    private  Integer code;
    private  String desc;

    @JsonValue
    public Integer getCode() {
        return code;
    }

    public String getDesc() {
        return desc;
    }

    AIResultTypeEnum(Integer code, String StatusMsg) {
        this.code = code;
        this.desc = StatusMsg;
    }
}
