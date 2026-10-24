package com.gientech.tools.database.infrastructure.enums;

import java.util.Objects;

/**
 * 数据库类型
 * @Author ： xiaomin.zuo@gientech.com
 * @date : 2025-7-14
 */
public enum DatabaseTypeEnum {

    MySQL("MySQL", "MySQL"),
    PostgreSQL("PostgreSQL", "PostgreSQL"),
    SQLServer("SQLServer", "SQLServer"),
    Doris("Doris", "Doris");

    private String code;
    private String desc;

    public String getCode() {
        return code;
    }

    public String getDesc() {
        return desc;
    }

    DatabaseTypeEnum(String code, String desc) {
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
