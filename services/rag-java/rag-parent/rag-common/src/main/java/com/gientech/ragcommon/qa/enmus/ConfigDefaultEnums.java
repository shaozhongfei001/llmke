package com.gientech.ragcommon.qa.enmus;

import com.fasterxml.jackson.annotation.JsonValue;

public enum ConfigDefaultEnums {

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

    ConfigDefaultEnums(Integer code, String StatusMsg) {
        this.code = code;
        this.desc = StatusMsg;
    }
    public static ConfigDefaultEnums of(int code){
        for (ConfigDefaultEnums oneScope : ConfigDefaultEnums.values()) {
            if(oneScope.getCode()==code){
                return oneScope;
            }
        }
        return null;
    }
}
