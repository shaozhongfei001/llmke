package com.gientech.ragcommon.graph.entity;

import lombok.Data;

import java.util.LinkedHashMap;

/**
 * @Description:
 * @Author: chenjuan
 * @Date: 2023/2/22 16:39
 */
@Data
public class NebulaNode {

    private String identity;

    private String label;

    private LinkedHashMap<String,Object> properties;
}
