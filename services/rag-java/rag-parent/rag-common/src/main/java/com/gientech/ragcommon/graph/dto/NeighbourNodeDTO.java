package com.gientech.ragcommon.graph.dto;

import com.alibaba.fastjson.JSONObject;
import lombok.Data;
import org.apache.commons.collections4.CollectionUtils;

import java.util.List;

/**
 * 邻居节点DTO
 */
@Data
public class NeighbourNodeDTO {
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
    private JSONObject properties;

    /**
     * 节点样式
     */
    private OntologyNodeDisplayInfoDTO displayData;

    private JSONObject style;

    private Float x;

    private Float y;

    /**
     * 节点关联的边
     */
    private List<EdgeDataDTO> edges;

    /**
     * 过滤边属性（weight属性）
     */
//    public void filterEdgeProperty() {
//        if(CollectionUtils.isNotEmpty(edges)){
//            for (EdgeDataDTO oneEdge : edges) {
//                oneEdge.removeWeightProperty();
//            }
//        }
//    }

    public NodeDataDTO toNodeDataDTO() {
        return NodeDataDTO.builder()
                .vid(vid)
                .name(name)
                .nodeType(nodeType)
                .properties(properties)
                .x(x)
                .y(y)
                .style(style)
                .build();

    }
}
