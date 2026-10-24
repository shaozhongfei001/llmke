package com.gientech.ragcommon.qa.enmus;

import com.fasterxml.jackson.annotation.JsonValue;

public enum ConfigenabledFaqEnums {

    YES(1,"是"),
    NO(0,"否");

    private  Integer code;
    private  String desc;

    @JsonValue
    public Integer getCode() {
        return code;
    }

    public String getDesc() {
        return desc;
    }

    ConfigenabledFaqEnums(Integer code, String StatusMsg) {
        this.code = code;
        this.desc = StatusMsg;
    }
    public static ConfigenabledFaqEnums of(int code){
        for (ConfigenabledFaqEnums oneScope : ConfigenabledFaqEnums.values()) {
            if(oneScope.getCode()==code){
                return oneScope;
            }
        }
        return null;
    }
}
