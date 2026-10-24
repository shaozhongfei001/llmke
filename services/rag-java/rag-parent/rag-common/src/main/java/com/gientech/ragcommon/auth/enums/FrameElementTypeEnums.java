package com.gientech.ragcommon.auth.enums;

import com.fasterxml.jackson.annotation.JsonValue;
import lombok.Getter;

@Getter
public enum FrameElementTypeEnums {
    DEPARTMENT(1, "部门"),
    GROUP(2, "用户组"),
    USER(3, "用户");

    @JsonValue
    private final Integer type;

    private final String desc;

    FrameElementTypeEnums(Integer type, String desc) {
        this.type = type;
        this.desc = desc;
    }

    public static FrameElementTypeEnums of(Integer type) {
        for (FrameElementTypeEnums value : FrameElementTypeEnums.values()) {
            if (value.getType().equals(type)) {
                return value;
            }
        }
        return null;
    }


}
