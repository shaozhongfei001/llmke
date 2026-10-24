package com.gientech.ragcommon.index.enmus;

public enum GraphParseStatusEnums {

    NORMAL(1,"正常"),
    PARSE_ING(2,"解析中"),
    PARSE_SUCCESS(3,"解析成功"),
    PARSE_FAIL(4,"解析失败");

    private Integer value;
    private String desc;

    public Integer getValue() {
        return value;
    }

    public String getDesc() {
        return desc;
    }

    GraphParseStatusEnums(Integer value, String StatusMsg) {
        this.value = value;
        this.desc = StatusMsg;
    }
    public static FaqExtractStatusEnums of(int code){
        for (FaqExtractStatusEnums oneScope : FaqExtractStatusEnums.values()) {
            if(oneScope.getValue()==code){
                return oneScope;
            }
        }
        return null;
    }
}
