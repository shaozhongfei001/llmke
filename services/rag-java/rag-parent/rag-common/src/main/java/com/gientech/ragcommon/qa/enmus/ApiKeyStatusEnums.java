package com.gientech.ragcommon.qa.enmus;

import lombok.Getter;

/**
 * apikey状态 状态 0:禁用；1:正常 默认值1
 */
@Getter
public enum ApiKeyStatusEnums {

    ENABLED( 1,"启用"),

    DISABLED( 0,"禁用");

    private Integer code;
    private String desc;

    ApiKeyStatusEnums(Integer code, String desc){
        this.code = code;
        this.desc = desc;
    }
}
