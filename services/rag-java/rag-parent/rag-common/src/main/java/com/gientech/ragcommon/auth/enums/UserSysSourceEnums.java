package com.gientech.ragcommon.auth.enums;

import com.fasterxml.jackson.annotation.JsonValue;
import lombok.Getter;

import java.util.Objects;

@Getter
public enum UserSysSourceEnums {

    AGENT(1, "agent平台");


    @JsonValue
    private Integer code;
    private String desc;

    UserSysSourceEnums(Integer code, String desc) {
        this.code = code;
        this.desc = desc;
    }

}


