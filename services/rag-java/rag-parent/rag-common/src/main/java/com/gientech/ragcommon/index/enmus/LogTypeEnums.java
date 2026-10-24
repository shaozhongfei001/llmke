package com.gientech.ragcommon.index.enmus;

public enum LogTypeEnums {

    FILE_PARSE(1, "文件解析"),
    FAQ_EXTRACT(2, "FAQ抽取"),
    FILE_GRAPH(3, "图数据生成"),
    ;
    private Integer code;
    private String desc;

    public Integer getCode() {
        return code;
    }

    public String getDesc() {
        return desc;
    }

    LogTypeEnums(Integer code, String statusMsg) {
        this.code = code;
        desc = statusMsg;
    }
}
