package com.gientech.ragcommon.graph.dto;

import lombok.Data;
import org.springframework.util.CollectionUtils;
import java.io.Serializable;
import java.util.List;

@Data
public class GraphDataStatisticsDTO implements Serializable {

    /**
     * 图谱名称
     */
    private String spaceName;

//    /**
//     * 图谱schema详情
//     */
//    private Object schemaDetail;
//
//    /**
//     * 节点列表
//     */
//    private List<GraphNodeStatisticsDTO> nodes;
//
//    /**
//     * 边列表
//     */
//    private List<GraphEdgeStatisticsDTO> edges;
//
//    /**
//     * 节点类型数量
//     */
//    private Integer nodeTypeAmount;

    /**
     * 节点实例数量（所有节点类型累加）
     */
    private Long nodeInstanceAmount;

    /**
     * 边类型数量
     */
//    private Integer edgeTypeAmount;

    /**
     * 边实例数量（所有边类型累加）
     */
    private Long edgeInstanceAmount;

    /**
     * 创建人
     */
    private String creator;


}
