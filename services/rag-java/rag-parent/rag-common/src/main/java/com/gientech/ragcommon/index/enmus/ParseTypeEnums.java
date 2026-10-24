package com.gientech.ragcommon.index.enmus;

public enum ParseTypeEnums {

    FILE_PARSE(1, "文件解析"),
    FAQ_PARSE(2, "faq抽取"),
    GRAPH_PARSE(3, "图解析"),
    DOC_QA(4, "文档上传问答"),
    FAQ_MANAGEMENT(5, "从文件解析复制的文件或者FAQ导入的问答对文件"),
    FAQ_FILE_PARSE(10, "文件解析&faq抽取"),;
    private Integer code;
    private String desc;

    public Integer getCode() {
        return code;
    }

    public String getDesc() {
        return desc;
    }

    ParseTypeEnums(Integer code, String statusMsg) {
        this.code = code;
        desc = statusMsg;
    }
}
