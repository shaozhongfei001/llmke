package com.gientech.ragcommon.index.enmus;

public enum FolderTypeEnums {

    //1:文档解析；2:FAQ抽取; 3;知识图谱 4:FAQ管理创建的文件夹或者从FAQ抽取复制的文件夹
    FILE_PARSE(1, "文档解析"),
    FAQ_EXTRACT(2, "FAQ抽取"),
    KB_GRAPH(3, "知识图谱"),
    FAQ_MANAGEMENT(4, "FAQ管理创建的文件夹或者从FAQ抽取复制的文件夹"),
    ;
    private Integer code;
    private String desc;

    public Integer getCode() {
        return code;
    }

    public String getDesc() {
        return desc;
    }

    FolderTypeEnums(Integer code, String statusMsg) {
        this.code = code;
        desc = statusMsg;
    }
}
