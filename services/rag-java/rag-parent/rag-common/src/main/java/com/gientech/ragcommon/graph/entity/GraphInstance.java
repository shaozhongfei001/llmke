package com.gientech.ragcommon.graph.entity;

import lombok.Data;

@Data
public class GraphInstance {

    /**
     * 文件id
     */
    private Long fileId;

    /**
     * 节点实例数
     */
    private  Integer nodeCount;

    /**
     * 边实例数
     */
    private Integer edgeCount;
}
