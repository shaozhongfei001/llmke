package com.gientech.ragcommon.qa.enmus;

import com.fasterxml.jackson.annotation.JsonValue;

public enum ReplyStatusEnums {

    RUN(1,"进行中"),
    PARSE_SUCCESS(2,"结束"),
    PARSE_FAIL(3,"异常");

    private final int code;
    private final String desc;

    @JsonValue
    public int getCode() {
        return code;
    }

    public String getDesc() {
        return desc;
    }

    ReplyStatusEnums(Integer code, String StatusMsg) {
        this.code = code;
        this.desc = StatusMsg;
    }
    public static ReplyStatusEnums of(int code){
        for (ReplyStatusEnums oneScope : ReplyStatusEnums.values()) {
            if(oneScope.getCode()==code){
                return oneScope;
            }
        }
        return null;
    }
}
