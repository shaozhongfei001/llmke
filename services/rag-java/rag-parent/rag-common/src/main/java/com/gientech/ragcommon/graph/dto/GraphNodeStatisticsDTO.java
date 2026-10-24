package com.gientech.ragcommon.graph.dto;

import lombok.Data;

import java.io.Serializable;


@Data
public class GraphNodeStatisticsDTO implements Serializable {

    /**
     * 节点名称
     */
    private String name;

    /**
     * 节点实例数量
     */
    private Long instanceAmount;

}
