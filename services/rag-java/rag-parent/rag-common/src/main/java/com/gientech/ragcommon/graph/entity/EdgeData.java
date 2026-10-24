package com.gientech.ragcommon.graph.entity;

import com.alibaba.fastjson.JSONObject;
import lombok.Data;

import java.util.List;

/**
 * 边数据实体类
 */
@Data
public class EdgeData {
    /**
     * 边类型
     */
    private String edgeType;

    private String name;

    /**
     * 边属性
     */
    private Object properties;

    /**
     * 起始点
     */
    private NodeData src;

    /**
     * 目的点
     */
    private NodeData dst;

    /**
     * rank值
     */
    private long rank;
}
