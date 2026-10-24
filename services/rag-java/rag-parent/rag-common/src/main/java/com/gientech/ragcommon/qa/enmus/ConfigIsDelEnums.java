package com.gientech.ragcommon.qa.enmus;



public enum ConfigIsDelEnums {

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

    ConfigIsDelEnums(Integer code, String desc) {
        this.code = code;
        this.desc = desc;
    }
}
