package com.gientech.raggraphservice.domain.service;

import java.io.UnsupportedEncodingException;
import java.util.List;

public interface GraphTemplate {
    /**
     * 判断节点/边类型是否存在
     *
     * @param label
     * @param isVertex true-vertex false-edge
     * @return
     */
    boolean isExistType(String subGraph, String label, boolean isVertex);

    /**
     * 获取节点或边的schema
     *
     * @param label
     * @param isVertex true-vertex false-edge
     * @return
     */
    String getLabelSchema(String subGraph, String label, boolean isVertex);

    /**
     * Schema构建
     *
     * @param schema
     * @return
     * @throws UnsupportedEncodingException
     */
    boolean importSchemaFromContent(String subGraph, String schema) throws UnsupportedEncodingException;

    /**
     * 执行语句,结果封装成json
     *
     * @param cypher
     * @return
     */
    String callCypher(String subGraph, String cypher);

    boolean deleteLabel(String subGraph, String label, boolean isVertex);

    boolean createGraph(String subGraph, String description);

    boolean isExistGraph(String subGraph);

    boolean isExistVertex(String subGraph,String vid);

    String getNodesByType(String subGraph,String label);

    boolean deleteGraph(String subGraph);

    boolean deleteBatchGraph(List<String> subGraphs);

    String getInstanceAmount(String subGraph);

    void cloneSpaceSchema(String destSubGraph, String srcSubGraph);

    String getVidType(String subGraph);
}
