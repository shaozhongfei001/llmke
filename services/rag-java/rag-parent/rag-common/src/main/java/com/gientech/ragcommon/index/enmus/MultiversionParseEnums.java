package com.gientech.ragcommon.index.enmus;

public enum MultiversionParseEnums {

    FILENAME("0", "只用根据文件名计算"),
    FILENAME_CONTENT("1", "文件名和内容一起计算"),;

    private String code;
    private String desc;

    public String getCode() {
        return code;
    }

    public String getDesc() {
        return desc;
    }

    MultiversionParseEnums(String code, String statusMsg) {
        this.code = code;
        desc = statusMsg;
    }
}
