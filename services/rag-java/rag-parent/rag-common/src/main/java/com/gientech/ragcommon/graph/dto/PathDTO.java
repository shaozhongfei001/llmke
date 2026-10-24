package com.gientech.ragcommon.graph.dto;

import com.fasterxml.jackson.annotation.JsonIgnore;
import lombok.Data;
import org.apache.commons.collections4.CollectionUtils;

import java.util.List;

/**
 * @Description:
 * @Author: chenjuan
 * @Date: 2023/3/17 18:08
 */
@Data
public class PathDTO {
    Long id;//标志一下数据行没有实际含义

    List<EdgeDataDTO> edges;

    List<NodeDataDTO> nodes;

    Integer step;

    String startNode;

    @JsonIgnore
    String endNode;

    String briefPath;

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

    public void generateEdgeId() {
        if (CollectionUtils.isEmpty(edges)) {
            return;
        }
        for(EdgeDataDTO oneEdge:edges){
            String id = oneEdge.getEdgeType() + "-" + oneEdge.getSrc().getVid() + "-" + oneEdge.getDst().getVid();
            oneEdge.setId(id);
        }
    }
}
