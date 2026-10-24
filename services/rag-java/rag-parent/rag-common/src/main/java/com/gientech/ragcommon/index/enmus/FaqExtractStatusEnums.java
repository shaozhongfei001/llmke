package com.gientech.ragcommon.index.enmus;

public enum FaqExtractStatusEnums {
    // faq抽取状态 1 未抽取；2 抽取中；3 抽取成功 4 抽取失败 默认值 1
    NO_EXTRACT(1,"未抽取"),
    EXTRACT_ING(2,"抽取中"),
    EXTRACT_SUCCESS(3,"抽取成功"),
    EXTRACT_FAIL(4,"抽取失败");

    private Integer value;
    private String desc;

    public Integer getValue() {
        return value;
    }

    public String getDesc() {
        return desc;
    }

    FaqExtractStatusEnums(Integer value, String StatusMsg) {
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
