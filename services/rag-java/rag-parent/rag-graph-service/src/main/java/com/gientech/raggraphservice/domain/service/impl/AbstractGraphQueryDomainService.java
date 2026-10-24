package com.gientech.raggraphservice.domain.service.impl;

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONArray;
import com.alibaba.fastjson.JSONObject;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.graph.dto.*;
import com.gientech.ragcommon.graph.entity.EdgeData;
import com.gientech.ragcommon.graph.entity.GraphData;
import com.gientech.ragcommon.graph.entity.NodeData;
import com.gientech.ragcommon.graph.entity.Property;
import com.gientech.ragcommon.infrastructure.exception.DomainException;
import com.gientech.raggraphservice.application.service.*;
import com.gientech.raggraphservice.domain.service.GraphQueryDomainService;
import com.gientech.raggraphservice.domain.service.GraphTemplate;
import com.google.common.collect.Lists;
import jakarta.annotation.Resource;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.collections4.CollectionUtils;
import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Service;

import java.util.*;


@Service
@Slf4j
public abstract class AbstractGraphQueryDomainService implements GraphQueryDomainService {

    @Resource
    private GraphTemplate graphTemplate;

    @Override
    public GraphData queryByCypher(String spaceName, String cypher,Long fileId) throws DomainException {
        /*校验 cypher ，只能是查询，不能是修改、插入、删除*/
        if (!cypher.trim().toUpperCase(Locale.ENGLISH).startsWith("MATCH")
                && !cypher.trim().toUpperCase(Locale.ENGLISH).startsWith("LOOKUP")
                && !cypher.trim().toUpperCase(Locale.ENGLISH).startsWith("GO")
                && !cypher.trim().toUpperCase(Locale.ENGLISH).startsWith("FETCH")
                && !cypher.trim().toUpperCase(Locale.ENGLISH).startsWith("SHOW")) {
            throw new DomainException(ErrCodeEnum.EXECUTE_GRAPH_QUERY_ERROR.getErrCode(), "查询语句必须以 MATCH，LOOKUP，GO，FETCH，SHOW 开头");
        }
        String cypherWithoutQuotesContent = cypher.trim().replaceAll("\\\"(.+)\\\"", "\"\"").replaceAll("\\\'(.+)\\\'", "''").toUpperCase();
        if (cypherWithoutQuotesContent.contains("INSERT") || cypherWithoutQuotesContent.contains("CREATE") ||
                cypherWithoutQuotesContent.contains("DELETE") || cypherWithoutQuotesContent.contains("SET") ||
                cypherWithoutQuotesContent.contains("REMOVE") || cypherWithoutQuotesContent.contains("MERGE")) {
            throw new DomainException(ErrCodeEnum.EXECUTE_GRAPH_QUERY_ERROR.getErrCode(), "查询语句中不能出现 INSERT,CREATE,DELETE,SET,REMOVE,MERGE 等关键字");
        }
        //如果没有 limit 则要加个limit
        if(!cypherWithoutQuotesContent.contains("LIMIT") && !cypher.trim().toUpperCase(Locale.ENGLISH).startsWith("SHOW")){
            if(cypher.lastIndexOf(";")>0){
                cypher = cypher.substring(0,cypher.lastIndexOf(";"));
            }
            if(cypher.trim().toUpperCase(Locale.ENGLISH).startsWith("GO") || cypher.trim().toUpperCase(Locale.ENGLISH).startsWith("LOOKUP")){
                cypher += " | ";
            }
            cypher += " limit 500 ";
        }
        try {
//            SchemaDTO ontology = ontologyAppService.getOntologyById(ontologyId);
            String resultStr = graphTemplate.callCypher(spaceName, cypher);
            log.info("resultStr:{}",resultStr);
            GraphData graphData = parseJsonToGraphData(spaceName, resultStr);
            //点查询还是边查询，如果是点查询要把相关的边查出来
            if (CollectionUtils.isEmpty(graphData.getEdgeList()) && CollectionUtils.isNotEmpty(graphData.getNodeList())) {
                //是点查询
                GraphData subGraph = getEdgesFromData(spaceName, graphData);
                graphData.setEdgeList(new ArrayList<>());
                if (CollectionUtils.isNotEmpty(subGraph.getEdgeList())) {
                    for (EdgeData edge : subGraph.getEdgeList()) {
                        if (!existEdge(graphData.getEdgeList(), edge)) {
                            graphData.getEdgeList().add(edge);
                        }
                    }
                    for (NodeData node : subGraph.getNodeList()) {
                        if (!existNode(graphData.getNodeList(), node)) {
                            graphData.getNodeList().add(node);
                        }
                    }
                }

            } else if (CollectionUtils.isNotEmpty(graphData.getEdgeList())) {
                //是边查询
                if (graphData.getNodeList() == null) {
                    graphData.setNodeList(new ArrayList<>());
                }
                for (EdgeData edge : graphData.getEdgeList()) {
                    if (!existNode(graphData.getNodeList(), edge.getSrc())) {
                        graphData.getNodeList().add(edge.getSrc());
                    }
                    if (!existNode(graphData.getNodeList(), edge.getDst())) {
                        graphData.getNodeList().add(edge.getDst());
                    }
                }
            }
            return graphData;
        } catch (Exception e) {
            log.error(e.getMessage(), e);
//            throw new DomainException(ErrCodeEnum.EXECUTE_GRAPH_QUERY_ERROR);
            throw new DomainException(ErrCodeEnum.EXECUTE_GRAPH_QUERY_ERROR.getErrCode(), e.getMessage());

        }
    }

    @Override
    public List<NodeData> queryNodesByIds(String spaceName, String cypher) throws DomainException {
        List<NodeData> nodeDatas = Lists.newArrayList();
        try {
            String resultStr = graphTemplate.callCypher(spaceName, cypher);
            log.info("resultStr:{}",resultStr);
            JSONArray dataArray = JSON.parseArray(resultStr);
            dataArray.forEach(dataJson -> {
                JSONObject json = ((JSONObject) dataJson).getJSONObject("v");
                String identity = json.getString("identity");
                String label = json.getString("label");
                JSONObject properties = json.getJSONObject("properties");
                NodeData nodeData = new NodeData();
                nodeData.setProperties(properties);
                nodeData.setVid(identity);
                nodeData.setNodeType(label);
                nodeDatas.add(nodeData);
            });
            return nodeDatas;
        } catch (Exception e) {
            log.error(e.getMessage(), e);
            throw new DomainException(ErrCodeEnum.EXECUTE_GRAPH_QUERY_ERROR.getErrCode(), e.getMessage());

        }
    }

    /**
     * 根据点查边
     *
     * @param spaceName
     * @param graphData
     * @return
     */
    abstract protected GraphData getEdgesFromData(String spaceName, GraphData graphData);

    /**
     * 把json解析成GraphData
     *
     * @param
     * @param result
     * @return
     */
    protected GraphData parseJsonToGraphData(String spaceName,String result) {
        return parseJsonToGraphData(spaceName,result, null);
    }

    /**
     * 把json解析成GraphData
     *
     * @param
     * @param result
     * @param conditionColNames 条件涉及到的字段名（用于标注查询直接命中的节点）
     * @return
     */
    protected GraphData parseJsonToGraphData(String spaceName,String result, List<String> conditionColNames) {
        List<NodeData> nodes = new ArrayList<>();
        List<EdgeData> edges = new ArrayList<>();
        parseJsonToGraphData(spaceName,result, nodes, edges, conditionColNames);
        GraphData graphData = new GraphData();
        graphData.setNodeList(nodes);
        graphData.setEdgeList(edges);
        graphData.setRawResult(result);
        return graphData;
    }

    protected void parseJsonToNodeData(String result, List<NodeData> nodes) {
        if (result.startsWith("[")) {
            JSONArray jsonArr = JSON.parseArray(result);
            for (int i = 0; i < jsonArr.size(); i++) {//每行
                JSONObject row = jsonArr.getJSONObject(i).getJSONObject("n");
                NodeData nodeData = new NodeData();
                JSONObject properties = row.getJSONObject("properties");
                nodeData.setNodeType(Objects.isNull(properties)? null : properties.getString("type"));
                nodeData.setVid(row.getString("identity"));
                nodeData.setProperties(properties);
                nodes.add(nodeData);
            }
        }
    }

    protected void parseJsonToGraphData(String spaceName,String result, List<NodeData> nodes, List<EdgeData> edges, List<String> conditionColNames) {
        if (result.startsWith("[")) {
            JSONArray jsonArr = JSON.parseArray(result);
            for (int i = 0; i < jsonArr.size(); i++) {//每行
                JSONObject row = jsonArr.getJSONObject(i);
                parseNodeAndEdge(spaceName,row, nodes, edges, conditionColNames);
            }
        } else {
            JSONObject row = JSON.parseObject(result);
            parseNodeAndEdge(spaceName,row, nodes, edges, conditionColNames);
        }
    }

    /**
     * 把查询出来的一行，把他解析到nodes 和 edges
     */
    protected void parseNodeAndEdge(
                                    String spaceName,
                                    JSONObject row,
                                    List<NodeData> nodes,
                                    List<EdgeData> edges,
                                    List<String> conditionColNames) {
        if (row == null) {
            return;
        }
        for (Iterator<Map.Entry<String, Object>> entryIter = row.entrySet().iterator(); entryIter.hasNext(); ) {
            Map.Entry<String, Object> entry = entryIter.next();
            String colName = entry.getKey();
            log.info("colName:" + colName);
            if (entry.getValue() instanceof JSONObject) {
                JSONObject jsonObj = (JSONObject) entry.getValue();
                parseJsonToNodeOrEdge(spaceName,nodes, edges, conditionColNames, colName, jsonObj);
            } else if (entry.getValue() instanceof JSONArray) {
                JSONArray jsonArray = (JSONArray) entry.getValue();
                for (Object obj : jsonArray) {
                    JSONObject jsonObj = (JSONObject) obj;
                    parseJsonToNodeOrEdge(spaceName,nodes, edges, conditionColNames, colName, jsonObj);
                }
            }
        }
    }

    /**
     * 把单个json对象分装成边或点
     *
     * @param
     * @param nodes
     * @param edges
     * @param conditionColNames
     * @param colName
     * @param jsonObj
     */
    private void parseJsonToNodeOrEdge(String spaceName,List<NodeData> nodes, List<EdgeData> edges, List<String> conditionColNames, String colName, JSONObject jsonObj) {
        Object desc = jsonObj.get("dst");
        if (desc != null) {//是边
            log.info("是边,desc:" + JSON.toJSON(desc) + ",\n jsonObj:" + JSON.toJSON(jsonObj));
            EdgeData edge = buildEdgeData(spaceName,jsonObj);
            if (!existEdge(edges, edge)) {
                edges.add(edge);
                NodeData src = edge.getSrc();
                NodeData dst = edge.getDst();
                if(!Objects.isNull(src))
                    nodes.add(src);
                if(!Objects.isNull(dst))
                    nodes.add(dst);
            }
        } else {//是节点
            log.info("是节点");
            NodeData node = buildNodeData(jsonObj);
            if (!existNode(nodes, node)) {
                nodes.add(node);
            }
            if (conditionColNames != null && conditionColNames.contains(colName)) {
                node = getNodeFromList(nodes, node);
                node.setHit(true);
            }
        }
    }

    private boolean existNode(List<NodeData> nodes, NodeData node) {
        for (NodeData n : nodes) {
            if (equalsNode(n, node)) {
                return true;
            }
        }
        return false;
    }

    private boolean equalsNode(NodeData node1, NodeData node2) {
        if (node1 == null && node2 == null) {
            return true;
        } else if (node1 == null && node2 != null || node1 != null && node2 == null) {
            return false;
        } else {
            return (node1.getNodeType().equals(node2.getNodeType()) && node1.getVid().equals(node2.getVid()));
        }

    }

    private NodeData getNodeFromList(List<NodeData> nodes, NodeData targetNode) {
        for (NodeData n : nodes) {
            if (equalsNode(n, targetNode)) {
                return n;
            }
        }
        return null;

    }

    private boolean existEdge(List<EdgeData> edges, EdgeData edge) {
        for (EdgeData e : edges) {
            NodeData src = e.getSrc();
            NodeData dst = e.getDst();
            if (e.getEdgeType().equals(edge.getEdgeType()) && equalsNode(e.getSrc(), edge.getSrc())
                    && equalsNode(e.getDst(), edge.getDst()) && e.getRank() == edge.getRank()) {
                return true;
            }
        }
        return false;
    }

    /**
     * 根据节点类型获取节点属性schema
     *
     * @param nodeType
     * @return
     */
    private JSONArray getNodePropertySchema(String subGraph, String nodeType) {
        String result = graphTemplate.getLabelSchema(subGraph, nodeType, true);
        JSONObject jsonObject = JSON.parseObject(result);
        JSONObject schema = jsonObject.getJSONObject("schema");
        JSONArray properties = schema.getJSONArray("properties");
        return properties;
    }


    /**
     * 生成节点数据实体类
     *
     * @param nodeObject
     * @param
     * @return
     */
    private NodeData buildNodeData(JSONObject nodeObject) {
        NodeData nodeData = new NodeData();
        nodeData.setVid(nodeObject.getString("identity"));
        nodeData.setNodeType(nodeObject.getString("label"));
        return nodeData;
    }

    private EdgeData buildEdgeData(String spaceName,JSONObject edgeObject) {
        EdgeData edgeData = new EdgeData();
        JSONObject properties = edgeObject.getJSONObject("properties");
        edgeData.setEdgeType(Objects.isNull(properties) ? "" : properties.getString("name"));
        edgeData.setProperties(properties);
        edgeData.setRank(edgeObject.getLong("rank"));

        // 获取头尾节点数据实体
        String vidType = getVidType(spaceName);
        String srcVid = edgeObject.getString("src");
        NodeData srcNode = getNodeDataByVid(spaceName, srcVid, vidType);
        edgeData.setSrc(srcNode);
        String dstVid = edgeObject.getString("dst");
        NodeData dstNode = getNodeDataByVid(spaceName, dstVid, vidType);
        edgeData.setDst(dstNode);
        return edgeData;
    }

    private NodeData getNodeDataByVid(String spaceName, String vidVal, String vidType) {
        String nGql;
        if (vidType.equals("INT64")) {
            nGql = "match (v) where id(v) == " + vidVal + " return v;";
        } else {
            nGql = "match (v) where id(v) == \"" + vidVal + "\" return v;";
        }

        String resultStr = graphTemplate.callCypher(spaceName, nGql);

        JSONArray jsonArray = JSON.parseArray(resultStr);
        if (jsonArray.size() > 0) {
            JSONObject jsonObject = jsonArray.getJSONObject(0);
            JSONObject nodeObject = jsonObject.getJSONObject("v");
            JSONObject properties = nodeObject.getJSONObject("properties");
            NodeData nodeData = new NodeData();
            nodeData.setVid(nodeObject.getString("identity"));
            nodeData.setNodeType(Objects.isNull(properties) ? null : properties.getString("type"));
            nodeData.setProperties(properties);
            return nodeData;
        }
        return null;
    }

    /**
     * 获取vid类型
     *
     * @param subGraph
     * @return
     */
    protected abstract String getVidType(String subGraph);
}
