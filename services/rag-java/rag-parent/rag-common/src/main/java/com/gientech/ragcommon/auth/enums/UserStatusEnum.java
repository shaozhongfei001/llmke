package com.gientech.ragcommon.auth.enums;

import java.util.Objects;

/**
 * 用户状态（ 1启用 0禁用）
 */
public enum UserStatusEnum {

    ENABLED(1, "启用"),
    DISENABLED(0, "禁用"),
    RESIGNED(-2,"已离职")
    ;

    private Integer code;
    private String desc;

    public Integer getCode() {
        return code;
    }

    public String getDesc() {
        return desc;
    }

    UserStatusEnum(Integer code, String desc) {
        this.code = code;
        this.desc = desc;
    }

    public static UserStatusEnum of(Integer code) {
        if (Objects.isNull(code)) {
            return null;
        }
        for (UserStatusEnum typeEnum : UserStatusEnum.values()) {
            if (Objects.equals(code, typeEnum.getCode())) {
                return typeEnum;
            }
        }
        return null;
    }
}
