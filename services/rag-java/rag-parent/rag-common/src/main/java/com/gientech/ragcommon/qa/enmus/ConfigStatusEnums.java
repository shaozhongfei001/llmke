package com.gientech.ragcommon.qa.enmus;

import com.fasterxml.jackson.annotation.JsonValue;

public enum ConfigStatusEnums {

    ENABLED(1,"启用"),
    DISABLE(0,"禁用");

    private  int code;
    private  String desc;

    @JsonValue
    public int getCode() {
        return code;
    }

    public String getDesc() {
        return desc;
    }

    ConfigStatusEnums(Integer code, String StatusMsg) {
        this.code = code;
        this.desc = StatusMsg;
    }
    public static ConfigStatusEnums of(int code){
        for (ConfigStatusEnums oneScope : ConfigStatusEnums.values()) {
            if(oneScope.getCode()==code){
                return oneScope;
            }
        }
        return null;
    }
}
