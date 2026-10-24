package com.gientech.ragcommon.auth.enums;


public enum StatusEnums {

    ENABLED(1, "启用"),
    DISENABLED(0, "禁用");

    private Integer code;
    private String desc;

    public Integer getCode() {
        return code;
    }

    public String getDesc() {
        return desc;
    }

    StatusEnums(Integer code, String desc) {
        this.code = code;
        this.desc = desc;
    }
}
