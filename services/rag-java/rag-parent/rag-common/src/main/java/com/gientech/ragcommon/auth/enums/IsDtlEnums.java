package com.gientech.ragcommon.auth.enums;



public enum IsDtlEnums {

    NO("0", "否"),
    YES("1", "是");


    private String code;
    private String desc;

    public String getCode() {
        return code;
    }

    public String getDesc() {
        return desc;
    }

    IsDtlEnums(String code, String desc) {
        this.code = code;
        this.desc = desc;
    }
}
