package com.gientech.ragcommon.index.enmus;

import java.util.Objects;

/**
 * 接入数据源类型
 * @Author ： xiaomin.zuo@gientech.com
 * @date : 2025-7-11
 */
public enum DataSourceTypeEnum {
    All("All", "所有类型数据源"),
    DataTable("DataTable", "数据表"),
    DirectDB("DirectDB", "数据库直连");

    private String code;
    private String desc;

    public String getCode() {
        return code;
    }

    public String getDesc() {
        return desc;
    }

    DataSourceTypeEnum(String code, String desc) {
        this.code = code;
        this.desc = desc;
    }

    public static DataSourceTypeEnum of(String code) {
        if (Objects.isNull(code)) {
            return null;
        }
        for (DataSourceTypeEnum typeEnum : DataSourceTypeEnum.values()) {
            if (Objects.equals(code, typeEnum.getCode())) {
                return typeEnum;
            }
        }
        return null;
    }

}
