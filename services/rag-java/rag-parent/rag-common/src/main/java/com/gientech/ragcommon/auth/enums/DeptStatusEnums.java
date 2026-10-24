package com.gientech.ragcommon.auth.enums;

public enum DeptStatusEnums {

    AWAITING_ACTIVATION(0, "待激活"),
    NORMAL(1, "正常"),
    DELETED(-1, "删除");

    private Integer code;
    private String desc;

    public Integer getCode() {
        return code;
    }

    public String getDesc() {
        return desc;
    }

    DeptStatusEnums(Integer code, String desc) {
        this.code = code;
        this.desc = desc;
    }
}
