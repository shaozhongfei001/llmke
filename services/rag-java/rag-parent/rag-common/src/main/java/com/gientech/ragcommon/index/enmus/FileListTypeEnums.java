package com.gientech.ragcommon.index.enmus;

public enum FileListTypeEnums {

    FILE_LIST(1, "文件解析列表"),
    FAQ_LIST(2, "faq解析列表"),
    GRAPH_LIST(3, "图解析列表"),
    DOC_QA(4, "文档上传问答"),
    ;
    private Integer code;
    private String desc;

    public Integer getCode() {
        return code;
    }

    public String getDesc() {
        return desc;
    }

    FileListTypeEnums(Integer code, String statusMsg) {
        this.code = code;
        desc = statusMsg;
    }
}
