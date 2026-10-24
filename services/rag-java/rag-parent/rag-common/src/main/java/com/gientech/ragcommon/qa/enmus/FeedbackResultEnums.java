package com.gientech.ragcommon.qa.enmus;

import com.fasterxml.jackson.annotation.JsonValue;

public enum FeedbackResultEnums {

    LIKE(1,"赞"),
    NU_LIKE(0,"踩");

    private  int code;
    private  String desc;

    @JsonValue
    public int getCode() {
        return code;
    }

    public String getDesc() {
        return desc;
    }

    FeedbackResultEnums(Integer code, String StatusMsg) {
        this.code = code;
        this.desc = StatusMsg;
    }
    public static FeedbackResultEnums of(int code){
        for (FeedbackResultEnums oneScope : FeedbackResultEnums.values()) {
            if(oneScope.getCode()==code){
                return oneScope;
            }
        }
        return null;
    }
}
