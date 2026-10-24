package com.gientech.ragcommon.auth.enums;

public enum RoleTypeEnums {

    SUPER_ADMIN(1, "超级管理员"),

    ADMIN(2, "管理员");

    private Integer code;
    private String desc;

    public Integer getCode() {
        return code;
    }

    public String getDesc() {
        return desc;
    }

    RoleTypeEnums(Integer code, String desc) {
        this.code = code;
        this.desc = desc;
    }
}
