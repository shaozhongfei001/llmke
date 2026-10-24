package com.gientech.ragcommon.qa.enmus;

import com.fasterxml.jackson.annotation.JsonValue;

public enum LlmTypeEnums {

    LLM_NORMAL(1,"正常的推理接口"),
    LLM_TABLE(2,"表格推理接口");

    private  int code;
    private  String desc;

    @JsonValue
    public int getCode() {
        return code;
    }

    public String getDesc() {
        return desc;
    }

    LlmTypeEnums(Integer code, String StatusMsg) {
        this.code = code;
        this.desc = StatusMsg;
    }
    public static LlmTypeEnums of(int code){
        for (LlmTypeEnums oneScope : LlmTypeEnums.values()) {
            if(oneScope.getCode()==code){
                return oneScope;
            }
        }
        return null;
    }
}
