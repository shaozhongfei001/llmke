package com.gientech.ragcommon.graph.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * @Description:
 * @Author: chenjuan
 * @Date: 2022/12/20 18:43
 */
@Data
@AllArgsConstructor
@NoArgsConstructor
public class OntologyEdgeDisplayInfoDTO {

    /**
     * 样式json
     */
    private String style;

    private Point startPoint;

    private Point endPoint;

    @Data
    public static class Point{
        private Float x;
        private Float y;
    }

}
