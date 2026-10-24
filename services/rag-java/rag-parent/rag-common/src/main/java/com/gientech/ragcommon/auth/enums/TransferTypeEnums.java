package com.gientech.ragcommon.auth.enums;

import com.fasterxml.jackson.annotation.JsonValue;
import lombok.Getter;

@Getter
public enum TransferTypeEnums {
    DELETE(1,"删除资源"),
    TRANSFER(2,"转移资源");

    @JsonValue
    private final Integer code;
    private final String desc;

    TransferTypeEnums(Integer code, String desc) {
        this.code = code;
        this.desc = desc;
    }


}
