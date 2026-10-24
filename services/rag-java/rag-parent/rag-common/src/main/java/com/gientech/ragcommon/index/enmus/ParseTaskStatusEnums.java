package com.gientech.ragcommon.index.enmus;

public enum ParseTaskStatusEnums {

    DELETED(-1, "删除"),
    PENDING(1, "待处理"),
    DEAL_ING(2, "处理中"),
    RETRY_ING(3, "重试中"),
    SUCESS(4, "处理成功"),
    DEAL_FAIL(5, "处理失败"),
    ;
    private Integer code;
    private String desc;

    public Integer getCode() {
        return code;
    }

    public String getDesc() {
        return desc;
    }

    ParseTaskStatusEnums(Integer code, String statusMsg) {
        this.code = code;
        desc = statusMsg;
    }
}
