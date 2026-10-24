package com.gientech.ragcommon.index.enmus;

public enum ModelStatusEnums {

    CHECK_ING(2, "检测中"),
    AVAILABLE(1, "可用"),
    UNAVAILABLE(0, "不可用");

    private Integer code;
    private String desc;

    public Integer getCode() {
        return code;
    }

    public String getDesc() {
        return desc;
    }

    ModelStatusEnums(Integer code, String desc) {
        this.code = code;
        this.desc = desc;
    }
}