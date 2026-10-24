package com.gientech.ragcommon.index.enmus;

import lombok.Getter;

public enum PlatFormEnums {

    INTELBRAIN_DW("intelbrain-dw", "智能写作"),
    RAG_QA("rag-qa", "知识问答");
    @Getter
    private String code;
    @Getter
    private String desc;

    private PlatFormEnums(String code, String desc) {
        this.code = code;
        this.desc = desc;
    }
}
