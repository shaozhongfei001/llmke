package com.gientech.ragcommon.graph.dto;


import com.alibaba.fastjson.JSONObject;
import com.fasterxml.jackson.annotation.JsonInclude;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.apache.commons.collections4.CollectionUtils;
import org.apache.commons.lang3.StringUtils;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

/**
 * 边数据DTO类
 */
@Data
@AllArgsConstructor
@NoArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class EdgeDataDTO {

    /**
     * 边标识，前端使用
     */
    private String id;

    /**
     * 边类型
     */
    private String edgeType;

    /**
     * 边属性
     */
//    private JSONObject properties;
    private Object properties;

    /**
     * 起始点
     */
    private NodeDataDTO src;

    /**
     * 目的点
     */
    private NodeDataDTO dst;

    /**
     * 边的样式
     */
    private OntologyEdgeDisplayInfoDTO displayData;

    /**
     * rank值
     */
    private Long rank;

    private String name;

    /**
     * 备注
     */
    private String remark;

    private JSONObject style;

    private OntologyEdgeDisplayInfoDTO.Point startPoint;

    private OntologyEdgeDisplayInfoDTO.Point endPoint;


//    public void removeWeightProperty() {
//        if (Objects.nonNull(properties)) {
//            properties.remove("weight");
//        }
//    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        EdgeDataDTO that = (EdgeDataDTO) o;
        return StringUtils.equals(edgeType, that.edgeType)
                && StringUtils.equals(src.getVid(), that.src.getVid())
                && StringUtils.equals(dst.getVid(), that.dst.getVid());
    }

    @Override
    public int hashCode() {
        if (StringUtils.isNotBlank(edgeType) && Objects.nonNull(src) && Objects.nonNull(dst)) {
            return Objects.hash(edgeType, src.getVid(), dst.getVid());
        } else {
            return super.hashCode();
        }
    }

    public String getId() {
        if (Objects.isNull(getSrc()) || Objects.isNull(getDst()))
            return this.getEdgeType();
        else
            return this.getSrc().getVid() + "-" + this.getEdgeType() + "-" + this.getDst().getVid() + "-" + this.getRank();
    }
}
