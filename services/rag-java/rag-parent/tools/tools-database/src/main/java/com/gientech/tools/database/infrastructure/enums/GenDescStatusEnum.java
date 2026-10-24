package com.gientech.tools.database.infrastructure.enums;

import com.alibaba.excel.util.StringUtils;
import lombok.Getter;

/**
 * @author: shirleychen
 * @date 2025/9/15 17:16
 * @description
 */
@Getter
public enum GenDescStatusEnum {
    SUCCESS("success", "成功"),
    FAIL("fail", "失败"),
    GENERATING("generating", "生成中");


    private String status;
    private String desc;

    GenDescStatusEnum(String status, String desc) {
        this.status = status;
        this.desc = desc;
    }

    public static GenDescStatusEnum of(String status) {
        if (StringUtils.isBlank(status)) {
            return null;
        }
        for (GenDescStatusEnum typeEnum : GenDescStatusEnum.values()) {
            if (typeEnum.status.equals(status)) {
                return typeEnum;
            }
        }
        return null;
    }
}
