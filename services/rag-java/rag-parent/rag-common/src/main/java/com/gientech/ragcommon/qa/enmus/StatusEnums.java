package com.gientech.ragcommon.qa.enmus;

import lombok.Getter;

@Getter
public enum StatusEnums {

    NORMAL( 1,"正常"),

    ERROR( 3,"异常"),
    DELETE(-1,"删除");

    private Integer code;
    private String desc;

    StatusEnums(Integer code, String desc){
        this.code = code;
        this.desc = desc;
    }


}
