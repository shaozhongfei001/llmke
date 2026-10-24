package com.gientech.ragcommon.index.enmus;

public enum FaqListDataTypeEnums {

    FOLDER(1, "文件夹"),
    FILE(2, "文件"),
    FAQ(3, "问答对"),
    ;
    private Integer code;
    private String desc;

    public Integer getCode() {
        return code;
    }

    public String getDesc() {
        return desc;
    }

    FaqListDataTypeEnums(Integer code, String statusMsg) {
        this.code = code;
        desc = statusMsg;
    }

    public static FaqListDataTypeEnums of(Integer code) {
        for (FaqListDataTypeEnums e : FaqListDataTypeEnums.values()) {
            if (e.code.equals(code)) {
                return e;
            }
        }
        return null;
    }
}
