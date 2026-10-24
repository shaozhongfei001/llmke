package com.gientech.ragcommon.graph.entity;

import lombok.Data;

@Data
public class SubGraphCenter {

    /**
     * 图空间
     */
    private String spaceName;

    /**
     * 中心点的vid
     */
    private String vid;

    /**
     * 中心点边的限制（10，或3）
     */
    private int edgeLimit;
}
