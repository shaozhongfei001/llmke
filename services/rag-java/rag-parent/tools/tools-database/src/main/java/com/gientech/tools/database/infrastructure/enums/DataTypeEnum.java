package com.gientech.tools.database.infrastructure.enums;

import java.sql.Types;

/**
 * 数据库字段类型枚举，对应java.sql.Types中的常量
 */
public enum DataTypeEnum {

    // 数值类型
    ARRAY("ARRAY", "数组类型"),
    BIGINT("BIGINT", "长整数"),
    BIT("BIT", "位（布尔值或二进制位）"),
    BOOLEAN("BOOLEAN", "布尔值（真/假）"),
    TINYINT("TINYINT", "微整数（如0-255范围）"),
    SMALLINT("SMALLINT", "小整数"),
    INTEGER("INTEGER", "整数"),
    FLOAT("FLOAT", "单精度浮点数"),
    REAL("REAL", "单精度浮点数（同FLOAT）"),
    DOUBLE("DOUBLE", "双精度浮点数"),
    NUMERIC("NUMERIC", "精确数值（同DECIMAL）"),
    DECIMAL("DECIMAL", "精确小数（如金额）"),

    // 字符类型
    CHAR("CHAR", "字符（定长字符串）"),
    VARCHAR("VARCHAR", "字符串（变长）"),
    LONGVARCHAR("LONGVARCHAR", "长字符串（变长）"),
    NCHAR("NCHAR", "Unicode字符（定长）"),
    NVARCHAR("NVARCHAR", "Unicode字符串（变长）"),
    LONGNVARCHAR("LONGNVARCHAR", "长Unicode字符串"),

    // 二进制类型
    BINARY("BINARY", "二进制数据（定长）"),
    VARBINARY("VARBINARY", "二进制数据（变长）"),
    LONGVARBINARY("LONGVARBINARY", "长二进制数据（变长）"),
    BLOB("BLOB", "二进制大对象（如图片、文件）"),
    CLOB("CLOB", "字符大对象（长文本）"),
    NCLOB("NCLOB", "Unicode字符大对象"),

    // 日期时间类型
    DATE("DATE", "日期（年月日）"),
    TIME("TIME", "时间（时分秒）"),
    TIMESTAMP("TIMESTAMP", "时间戳（日期+时间）"),
    TIME_WITH_TIMEZONE("TIME_WITH_TIMEZONE", "带时区的时间"),
    TIMESTAMP_WITH_TIMEZONE("TIMESTAMP_WITH_TIMEZONE", "带时区的时间戳");


    private final String code;
    private final String description;

    DataTypeEnum(String code, String description) {
        this.code = code;
        this.description = description;
    }

    /**
     * 获取类型对应的码值
     */
    public String getCode() {
        return code;
    }

    /**
     * 获取类型的中文描述
     */
    public String getDescription() {
        return description;
    }

    /**
     * 根据码值获取对应的枚举实例
     */
    public static DataTypeEnum getByCode(String code) {
        for (DataTypeEnum type : values()) {
            if (type.code == code) {
                return type;
            }
        }
        return null;
    }
}
