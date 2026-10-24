package com.gientech.ragcommon.index.enmus;

public enum KbTypeEnums {
    KB(1, "知识库"),
    DOC_QA(2, "文档上传问答"),
            ;
    private Integer code;
    private String desc;

    public Integer getCode() {
        return code;
    }

    public String getDesc() {
        return desc;
    }

    KbTypeEnums(Integer code, String statusMsg) {
        this.code = code;
        desc = statusMsg;
    }
}
