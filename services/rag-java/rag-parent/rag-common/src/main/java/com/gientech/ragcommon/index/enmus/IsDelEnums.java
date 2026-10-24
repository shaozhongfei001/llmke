package com.gientech.ragcommon.index.enmus;

public enum IsDelEnums {

    NORMAL(1, "正常"),
    DELETE(-1, "删除"),;
    private Integer code;
    private String desc;

    public Integer getCode() {
        return code;
    }

    public String getDesc() {
        return desc;
    }

    IsDelEnums(Integer code, String statusMsg) {
        this.code = code;
        desc = statusMsg;
    }
}
