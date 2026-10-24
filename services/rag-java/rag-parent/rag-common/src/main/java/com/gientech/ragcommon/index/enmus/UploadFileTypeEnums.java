package com.gientech.ragcommon.index.enmus;

public enum UploadFileTypeEnums {

    SKIP("skip", "跳过"),
    OVERWRITE("overwrite", "覆盖"),
    NEWVERSION("newVersion", "新版本"),
    ;
    private String code;
    private String desc;

    public String getCode() {
        return code;
    }

    public String getDesc() {
        return desc;
    }

    UploadFileTypeEnums(String code, String desc) {
        this.code = code;
        this.desc = desc;
    }
}
