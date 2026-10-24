package com.gientech.ragcommon.index.enmus;

public enum DataBaseTypePrefixEnums {

    // faq抽取状态 1 未抽取；2 抽取中；3 抽取成功 4 抽取失败 默认值 1
    KNOWLEDGE_BASE("kb_","知识库"),
    DATA_BASE("db_","数据库");

    private String value;
    private String desc;

    public String getValue() {
        return value;
    }

    public String getDesc() {
        return desc;
    }

    DataBaseTypePrefixEnums(String value, String desc) {
        this.value = value;
        this.desc = desc;
    }

}
