package com.gientech.ragcommon.graph.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;

/**
 * @Descrption:
 * @Author:liutaiyun
 * @Date:2022/08/20 15:33
 **/

@Data
@AllArgsConstructor
@NoArgsConstructor
public class OntologyNodeDisplayInfoDTO implements Serializable,Cloneable {

    /**
     * X轴坐标
     */
    private Float x;

    /**
     * Y轴坐标
     */
    private Float y;

    /**
     * 样式json
     */
    private String style;

    /**
     * R轴坐标
     */
    //private String r;

    /**
     * 颜色
     */
    //private String color;

    @Override
    public Object clone() throws CloneNotSupportedException {
        return super.clone();
    }
}
