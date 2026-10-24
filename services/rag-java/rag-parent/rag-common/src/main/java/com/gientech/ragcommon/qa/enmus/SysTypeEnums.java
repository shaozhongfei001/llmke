package com.gientech.ragcommon.qa.enmus;


import lombok.Getter;

@Getter
public enum SysTypeEnums{

    INT_SESSION( 0,"智能会话"),

    KNO_INDEX(1,"知识索引"),

    TEMPORARY(2,"临时会话"),

    RETRIEVE_RECALL_TEST(3,"知识检索召回测试"),;

    private Integer code;
    private String desc;

    SysTypeEnums(Integer code, String desc){
        this.code = code;
        this.desc = desc;
    }

}
