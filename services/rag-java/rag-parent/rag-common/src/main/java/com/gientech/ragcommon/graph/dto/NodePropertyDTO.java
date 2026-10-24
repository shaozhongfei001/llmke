package com.gientech.ragcommon.graph.dto;

import com.fasterxml.jackson.databind.annotation.JsonSerialize;
import com.fasterxml.jackson.databind.ser.std.ToStringSerializer;
import lombok.Data;

import java.io.Serializable;

@Data
public class NodePropertyDTO implements Serializable {

    /**
     * 主键
     */
    @JsonSerialize(using = ToStringSerializer.class)
    private Long id;

    /**
     * 具体的内容，名称
     */
    private String name;

    /**
     * 具体的内容，类型
     */
    private String type;

    @JsonSerialize(using = ToStringSerializer.class)
    private Long nodeId;

    /**
     * 是否是主键
     */
    private Boolean primaryKey;

    /**
     * 是否是选填
     */
    private Boolean optional;

    /**
     * 是否展示字段
     */
    private Boolean displayField = false;
}
