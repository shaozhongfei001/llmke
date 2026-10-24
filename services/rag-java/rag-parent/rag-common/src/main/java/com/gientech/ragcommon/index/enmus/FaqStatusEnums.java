package com.gientech.ragcommon.index.enmus;

public enum FaqStatusEnums {

    DISABLED(0, "禁用"),
    ENABLED(1, "启用"),;
    private Integer code;
    private String desc;

    public Integer getCode() {
        return code;
    }

    public String getDesc() {
        return desc;
    }

    FaqStatusEnums(Integer code, String statusMsg) {
        this.code = code;
        desc = statusMsg;
    }
}
