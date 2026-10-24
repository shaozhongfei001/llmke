package com.gientech.ragcommon.qa.enmus;

import com.fasterxml.jackson.annotation.JsonValue;

public enum DialogueStatusEnums {

    NORMAL(1,"正常"),
    DELETE(0,"删除");

    private  int code;
    private  String desc;

    @JsonValue
    public int getCode() {
        return code;
    }

    public String getDesc() {
        return desc;
    }

    DialogueStatusEnums(Integer code, String StatusMsg) {
        this.code = code;
        this.desc = StatusMsg;
    }
    public static DialogueStatusEnums of(int code){
        for (DialogueStatusEnums oneScope : DialogueStatusEnums.values()) {
            if(oneScope.getCode()==code){
                return oneScope;
            }
        }
        return null;
    }
}
