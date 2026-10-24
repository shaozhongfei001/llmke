package com.gientech.ragcommon.auth.enums;

import lombok.Getter;

import java.util.Objects;

/**
 * 逻辑删除 是否删除 1是 0 未删除
 */
public enum UserIsDelEnum {

    YES(1, "是"),
    NO(0, "否"),
    ;

    private Integer code;
    private String desc;

    public Integer getCode() {
        return code;
    }

    public String getDesc() {
        return desc;
    }

    UserIsDelEnum(Integer code, String desc) {
        this.code = code;
        this.desc = desc;
    }

    public static UserIsDelEnum of(Integer code) {
        if (Objects.isNull(code)) {
            return null;
        }
        for (UserIsDelEnum typeEnum : UserIsDelEnum.values()) {
            if (Objects.equals(code, typeEnum.getCode())) {
                return typeEnum;
            }
        }
        return null;
    }
}
