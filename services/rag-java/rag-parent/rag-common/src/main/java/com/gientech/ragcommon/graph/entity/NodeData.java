package com.gientech.ragcommon.graph.entity;

import com.alibaba.fastjson.JSONObject;
import lombok.Data;

/**
 * 节点数据实体类
 */
@Data
public class NodeData {
    /**
     * 节点vid
     */
    private String vid;

    private String name;

    /**
     * 节点类型（Nebula Tag名)
     */
    private String nodeType;

    /**
     * 节点属性
     */
    private Object properties;

    /**
     * 是否查询条件直接命中的（为false则为通过关系带出来的）
     */
    private boolean hit;
}
