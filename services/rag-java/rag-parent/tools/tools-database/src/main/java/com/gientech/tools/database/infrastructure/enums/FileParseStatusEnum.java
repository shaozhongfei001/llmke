package com.gientech.tools.database.infrastructure.enums;

import java.util.Objects;

/**
 * 上传文件导入状态
 */
public enum FileParseStatusEnum {
    S00("00", "导入失败"),
    S10("10", "待导入"),
    S11("11", "导入中未创建表"),
    S20("20", "导入中"),
    S30("30", "导入成功");

    private String code;
    private String desc;

    public String getCode() {
        return code;
    }

    public String getDesc() {
        return desc;
    }

    FileParseStatusEnum(String code, String desc) {
        this.code = code;
        this.desc = desc;
    }

    public static DatabaseTypeEnum of(String code) {
        if (Objects.isNull(code)) {
            return null;
        }
        for (DatabaseTypeEnum typeEnum : DatabaseTypeEnum.values()) {
            if (Objects.equals(code, typeEnum.getCode())) {
                return typeEnum;
            }
        }
        return null;
    }
}
