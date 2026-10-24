package com.gientech.ragcommon.graph.dto;

import com.alibaba.fastjson.JSONArray;
import com.alibaba.fastjson.JSONObject;
import com.fasterxml.jackson.annotation.JsonInclude;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;
import java.util.Objects;

/**
 * 节点数据DTO类
 */
@Data
@Builder
@AllArgsConstructor
@NoArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class NodeDataDTO {
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
     * 是否查询条件直接命中的（为false则为通过关系带出来的）
     */
    private boolean hit;

    /**
     * 节点属性
     */
//    private JSONObject properties;
    private Object properties;

    /**
     * 节点样式
     */
//    private OntologyNodeDisplayInfoDTO displayData;

    private JSONObject style;

    private Float x;

    private Float y;
    /**
     * 备注
     */
    private String remark;

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        NodeDataDTO that = (NodeDataDTO) o;
        return hit == that.hit && Objects.equals(vid, that.vid);
    }

    @Override
    public int hashCode() {
        return Objects.hash(vid, name, nodeType, hit, properties, style, remark);
    }

    public NodeDataDTO(String vid) {
        this.vid = vid;
    }

}
