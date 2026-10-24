package com.gientech.ragcommon.auth.enums;

import lombok.Getter;

import java.util.Objects;

public enum ResourceTypeEnum {

//    /**
//     * 操作
//     */
//    OPER(1, "OPER"),
//
//    /**
//     * 菜单
//     */
//    MENU(2, "MENU");

    /**
     * 菜单
     */
    MENU(1, "MENU"),

    /**
     * 操作
     */
    OPER(2, "OPER");

    private Integer code;
    private String desc;

    public Integer getCode() {
        return code;
    }

    public String getDesc() {
        return desc;
    }

    ResourceTypeEnum(Integer code, String desc) {
        this.code = code;
        this.desc = desc;
    }

    public static ResourceTypeEnum of(String code) {
        if (Objects.isNull(code)) {
            return null;
        }
        for (ResourceTypeEnum typeEnum : ResourceTypeEnum.values()) {
            if (Objects.equals(code, typeEnum.getCode())) {
                return typeEnum;
            }
        }
        return null;
    }

}
