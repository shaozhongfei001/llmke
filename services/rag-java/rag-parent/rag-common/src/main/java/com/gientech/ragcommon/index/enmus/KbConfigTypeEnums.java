package com.gientech.ragcommon.index.enmus;

public enum KbConfigTypeEnums {

    FILE_PARSE(1, "文件解析配置"),
    FAQ(2, "FAQ配置"),
    GRAPH(3, "知识图谱配置"),
    ;
    private Integer code;
    private String desc;

    public Integer getCode() {
        return code;
    }

    public String getDesc() {
        return desc;
    }

    KbConfigTypeEnums(Integer code, String statusMsg) {
        this.code = code;
        desc = statusMsg;
    }
}
