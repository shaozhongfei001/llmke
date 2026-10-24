package com.gientech.ragcommon.index.enmus;

import com.fasterxml.jackson.annotation.JsonValue;
import lombok.Getter;

@Getter
public enum PermissionEnums {
    NO_PERMISSION(0, "无权限"),
    READ(1, "可阅读"),
    READ_WRITE(2, "可编辑"),
    ALL(3, "可管理");
    @JsonValue
    private Integer code;
    private String desc;

    PermissionEnums(Integer code, String desc) {
        this.code = code;
        this.desc = desc;
    }

    public static PermissionEnums of(Integer code) {
        for (PermissionEnums value : values()) {
            if (value.getCode().equals(code)) {
                return value;
            }
        }
        return null;
    }
}
