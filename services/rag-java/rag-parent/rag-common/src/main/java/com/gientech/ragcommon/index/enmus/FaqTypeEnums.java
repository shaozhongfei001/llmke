package com.gientech.ragcommon.index.enmus;

public enum FaqTypeEnums {

    SOURCE_FAQ(1, "原faq"),
    SIMILAR_QUESTION(2, "相似问"),
    ;
    private Integer code;
    private String desc;

    public Integer getCode() {
        return code;
    }

    public String getDesc() {
        return desc;
    }

    FaqTypeEnums(Integer code, String statusMsg) {
        this.code = code;
        desc = statusMsg;
    }

    public static FaqTypeEnums of(Integer code) {
        for (FaqTypeEnums e : FaqTypeEnums.values()) {
            if (e.code.equals(code)) {
                return e;
            }
        }
        return null;
    }
}
