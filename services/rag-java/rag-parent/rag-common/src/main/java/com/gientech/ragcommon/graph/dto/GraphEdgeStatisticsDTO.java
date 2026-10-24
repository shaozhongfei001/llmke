package com.gientech.ragcommon.graph.dto;

import lombok.Data;

import java.io.Serializable;

/**
 * @Descrption:
 * @Author:liutaiyun
 * @Date:2023/03/01 10:50
 **/
@Data
public class GraphEdgeStatisticsDTO implements Serializable {

    /**
     * 边名称
     */
    private String name;

    /**
     * 边实例数量
     */
    private Long instanceAmount;

}
