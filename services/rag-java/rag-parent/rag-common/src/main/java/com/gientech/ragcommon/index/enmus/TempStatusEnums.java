package com.gientech.ragcommon.index.enmus;

public enum TempStatusEnums {

    TEMP(1, "临时"),
    PERSISTENCE(2, "持久化文件"),
    ;
    private Integer code;
    private String desc;

    public Integer getCode() {
        return code;
    }

    public String getDesc() {
        return desc;
    }

    TempStatusEnums(Integer code, String statusMsg) {
        this.code = code;
        desc = statusMsg;
    }
}
