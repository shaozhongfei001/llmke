package com.gientech.ragcommon.index.enmus;

/**
 * 文件启动用/禁用
 */
public enum KbFileEnableEnums {

    DISABLE(0, "禁用"),
    ENABLE(1, "启用"),;
    private Integer code;
    private String desc;

    public Integer getCode() {
        return code;
    }

    public String getDesc() {
        return desc;
    }

    KbFileEnableEnums(Integer code, String statusMsg) {
        this.code = code;
        desc = statusMsg;
    }
}
