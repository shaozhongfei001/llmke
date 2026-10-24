package com.gientech.ragcommon.graph.entity;

import lombok.Data;

/**
 * 节点或边的属性实体类
 */
@Data
public class Property {

    /**
     * 属性名
     */
    private String name;

    /**
     * 属性值
     */
    private Object value;

    /**
     * 类型
     */
    private String type;

    /**
     * 是否主键
     */
    private Boolean primaryKey;

    private Boolean displayField;
}
