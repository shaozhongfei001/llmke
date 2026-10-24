package com.gientech.ragcommon.auth.enums;



public enum GroupIsDelEnums {

    NO(1, "否"),
    YES(-1, "是");


    private Integer code;
    private String desc;

    public Integer getCode() {
        return code;
    }

    public String getDesc() {
        return desc;
    }

    GroupIsDelEnums(Integer code, String desc) {
        this.code = code;
        this.desc = desc;
    }
}
