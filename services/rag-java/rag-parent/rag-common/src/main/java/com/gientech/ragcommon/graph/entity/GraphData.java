package com.gientech.ragcommon.graph.entity;

import lombok.Data;

import java.util.List;

/**
 * 图数据实体类
 */
@Data
public class GraphData {

    /**
     * 节点列表
     */
    private List<NodeData> nodeList;

    /**
     * 边列表
     */
    private List<EdgeData> edgeList;

    /**
     * 原始查询结果。执行cypher语句，nebula api返回的原始数据
     */
    private String rawResult;
}
