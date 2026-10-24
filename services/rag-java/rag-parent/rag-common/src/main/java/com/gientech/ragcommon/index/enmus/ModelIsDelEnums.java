package com.gientech.ragcommon.index.enmus;

public enum ModelIsDelEnums {

    NORMAL("0", "未删除"),
    DELETE("1", "已删除"),;
    private String code;
    private String desc;

    public String getCode() {
        return code;
    }

    public String getDesc() {
        return desc;
    }

    ModelIsDelEnums(String code, String statusMsg) {
        this.code = code;
        desc = statusMsg;
    }
}
