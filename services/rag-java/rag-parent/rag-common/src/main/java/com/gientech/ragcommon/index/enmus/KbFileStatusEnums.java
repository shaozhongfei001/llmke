package com.gientech.ragcommon.index.enmus;

public enum KbFileStatusEnums {

    DELETE(0,"已删除"),
    NORMAL(1,"正常"),
    PARSE_ING(2,"解析中"),
    PARSE_SUCCESS(3,"解析成功"),
    PARSE_FAIL(4,"解析失败"),
    RE_EMBEDDING_ING(5, "重新向量化"),

    RETRY(98, "重试中"),
    PARSE_WAIT(99, "解析排队中")
    ;

    private Integer value;
    private String desc;

    public Integer getValue() {
        return value;
    }

    public String getDesc() {
        return desc;
    }

    KbFileStatusEnums(Integer value, String StatusMsg) {
        this.value = value;
        this.desc = StatusMsg;
    }
    public static KbFileStatusEnums of(int code){
        for (KbFileStatusEnums oneScope : KbFileStatusEnums.values()) {
            if(oneScope.getValue()==code){
                return oneScope;
            }
        }
        return null;
    }
}
