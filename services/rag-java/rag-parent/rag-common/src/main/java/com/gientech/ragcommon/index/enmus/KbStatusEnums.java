package com.gientech.ragcommon.index.enmus;

public enum KbStatusEnums {

    DELETE(0,"已删除"),
    NORMAL(1,"正常");

    private Integer value;
    private String desc;

    public Integer getValue() {
        return value;
    }

    public String getDesc() {
        return desc;
    }

    KbStatusEnums(Integer value, String StatusMsg) {
        this.value = value;
        this.desc = StatusMsg;
    }
    public static KbStatusEnums of(int code){
        for (KbStatusEnums oneScope : KbStatusEnums.values()) {
            if(oneScope.getValue()==code){
                return oneScope;
            }
        }
        return null;
    }
}
