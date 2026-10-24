package com.gientech.ragcommon.graph.entity;

import lombok.Data;

import java.util.LinkedHashMap;

/**
 * @Description:
 * @Author: chenjuan
 * @Date: 2023/2/22 16:50
 */
@Data
public class NebulaEdge {
    private String src;
    private String dst;
    private boolean forward;
    private String label_id;
    private String label_name;
    private long rank;
    private LinkedHashMap<String,Object> properties;
}
