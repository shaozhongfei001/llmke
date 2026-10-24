package com.gientech.raggraphservice.infrastructure;

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONArray;
import com.alibaba.fastjson.JSONObject;
import com.gientech.ragcommon.graph.dto.EdgePropertyDTO;
import com.gientech.ragcommon.graph.dto.NodePropertyDTO;
import com.gientech.ragcommon.graph.entity.EdgeData;
import com.gientech.ragcommon.graph.entity.GraphData;
import com.gientech.ragcommon.graph.entity.NodeData;
import com.gientech.ragcommon.graph.entity.Property;
import com.gientech.raggraphservice.domain.service.GraphTemplate;
import com.gientech.raggraphservice.domain.service.impl.NebulaGraphTemplate;
import com.google.common.collect.Lists;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.util.*;

@Slf4j
@Component
public class GraphDataParser {

    @Autowired
    private GraphTemplate graphTemplate;


    /**
     * 把json解析成GraphData
     *
     * @param spaceName
     * @param result
     * @return
     */
    public GraphData parseJsonToGraphData(String spaceName, String result) {
        return parseJsonToGraphData(spaceName, result, null,true);
    }

    /**
     * 把json解析成GraphData
     *
     * @param spaceName
     * @param result
     * @param conditionColNames 条件涉及到的字段名（用于标注查询直接命中的节点）
     * @return
     */
    public GraphData parseJsonToGraphData(String spaceName, String result, List<String> conditionColNames,boolean edgeNeedSrcAndDst) {
        List<NodeData> nodes = new ArrayList<>();
        List<EdgeData> edges = new ArrayList<>();
        parseJsonToGraphData(spaceName, result, nodes, edges, conditionColNames,edgeNeedSrcAndDst);
        GraphData graphData = new GraphData();
        graphData.setNodeList(nodes);
        graphData.setEdgeList(edges);
        graphData.setRawResult(result);
        return graphData;
    }

    public void parseJsonToGraphData(String spaceName, String result, List<NodeData> nodes, List<EdgeData> edges, List<String> conditionColNames,boolean edgeNeedSrcAndDst) {
        if (result.startsWith("[")) {
            JSONArray jsonArr = JSON.parseArray(result);
            Map<String, List<NodePropertyDTO>> nodePropertiesMap = new HashMap<>();
            Map<String, List<EdgePropertyDTO>> edgePropertiesMap = new HashMap<>();
            for (int i = 0; i < jsonArr.size(); i++) {//每行
                JSONObject row = jsonArr.getJSONObject(i);
                parseNodeAndEdge(spaceName, row, nodes, edges, nodePropertiesMap, edgePropertiesMap, conditionColNames,edgeNeedSrcAndDst);
            }
        } else {
            JSONObject row = JSON.parseObject(result);
            Map<String, List<NodePropertyDTO>> nodePropertiesMap = new HashMap<>();
            Map<String, List<EdgePropertyDTO>> edgePropertiesMap = new HashMap<>();
            parseNodeAndEdge(spaceName, row, nodes, edges, nodePropertiesMap, edgePropertiesMap, conditionColNames,edgeNeedSrcAndDst);
        }
    }

    /**
     * 把查询出来的一行，把他解析到nodes 和 edges
     */
    protected void parseNodeAndEdge(String spaceName,
                                    JSONObject row,
                                    List<NodeData> nodes,
                                    List<EdgeData> edges,
                                    Map<String, List<NodePropertyDTO>> nodePropertiesMap,
                                    Map<String, List<EdgePropertyDTO>> edgePropertiesMap, List<String> conditionColNames,
                                    boolean edgeNeedSrcAndDst
    ) {
        if (row == null) {
            return;
        }
        for (Iterator<Map.Entry<String, Object>> entryIter = row.entrySet().iterator(); entryIter.hasNext(); ) {
            Map.Entry<String, Object> entry = entryIter.next();
            String colName = entry.getKey();
            log.info("colName:" + colName);
            if (entry.getValue() instanceof JSONObject) {
                JSONObject jsonObj = (JSONObject) entry.getValue();
                parseJsonToNodeOrEdge(spaceName, nodes, edges, nodePropertiesMap, edgePropertiesMap, conditionColNames, colName, jsonObj,edgeNeedSrcAndDst);
            } else if (entry.getValue() instanceof JSONArray) {
                JSONArray jsonArray = (JSONArray) entry.getValue();
                for (Object obj : jsonArray) {
                    JSONObject jsonObj = (JSONObject) obj;
                    parseJsonToNodeOrEdge(spaceName, nodes, edges, nodePropertiesMap, edgePropertiesMap, conditionColNames, colName, jsonObj,edgeNeedSrcAndDst);
                }
            }
        }
    }

    /**
     * 把单个json对象分装成边或点
     *
     * @param spaceName
     * @param nodes
     * @param edges
     * @param nodePropertiesMap
     * @param edgePropertiesMap
     * @param conditionColNames
     * @param colName
     * @param jsonObj
     */
    private void parseJsonToNodeOrEdge(String spaceName, List<NodeData> nodes, List<EdgeData> edges, Map<String, List<NodePropertyDTO>> nodePropertiesMap, Map<String, List<EdgePropertyDTO>> edgePropertiesMap, List<String> conditionColNames, String colName, JSONObject jsonObj,boolean edgeNeedSrcAndDst) {
        Object desc = jsonObj.get("dst");
        if (desc != null) {//是边
            log.info("是边,desc:" + JSON.toJSON(desc) + ",\n jsonObj:" + JSON.toJSON(jsonObj));
            String edgeType = jsonObj.getString("label_name");
            List<EdgePropertyDTO> edgeProperties = edgePropertiesMap.get(edgeType);
            if (edgeProperties == null) {
                edgeProperties = getEdgeProperties(spaceName, edgeType);
                edgePropertiesMap.put(edgeType, edgeProperties);
            }
            EdgeData edge = buildEdgeData(spaceName, jsonObj, edgeProperties, nodePropertiesMap,nodes,edgeNeedSrcAndDst);
            if (!existEdge(edges, edge)) {
                edges.add(edge);
            }
        } else {//是节点
            log.info("是节点");
            String nodeType = jsonObj.getString("label");
            List<NodePropertyDTO> nodeProperties = nodePropertiesMap.get(nodeType);
            if (nodeProperties == null) {
                nodeProperties = getNodeProperties(spaceName, nodeType);
                nodePropertiesMap.put(nodeType, nodeProperties);
            }
            NodeData node = buildNodeData(jsonObj, nodeProperties);
            if (!existNode(nodes, node)) {
                nodes.add(node);
            }
            if (conditionColNames != null && conditionColNames.contains(colName)) {
                node = getNodeFromList(nodes, node);
                node.setHit(true);
            }
        }
    }


    /**
     * 获取属性
     *
     * @param spaceName
     * @param edgeType
     * @return
     */
    protected List<EdgePropertyDTO> getEdgeProperties(String spaceName, String edgeType) {
        String cypher = "DESC edge " + edgeType;
        String result = graphTemplate.callCypher(spaceName, cypher);
        List<EdgePropertyDTO> resultList = new ArrayList<>();
        if(StringUtils.isNotBlank(result)){
            List<JSONObject> edgeProperties = JSON.parseArray(result, JSONObject.class);
            for (JSONObject edgeProperty : edgeProperties) {
                EdgePropertyDTO edgePropertyDTO = new EdgePropertyDTO();
                edgePropertyDTO.setName(edgeProperty.getString("Field"));
                edgePropertyDTO.setType(edgeProperty.getString("int64"));
                resultList.add(edgePropertyDTO);
            }
        }
        return resultList;
    }


    private EdgeData buildEdgeData(String subGraph, JSONObject edgeObject, JSONArray edgePropertySchema, Map<String, JSONArray> nodePropertySchemaMap) {
        EdgeData edgeData = new EdgeData();
        edgeData.setEdgeType(edgeObject.getString("label_name"));
        JSONObject propertyObject = edgeObject.getJSONObject("properties");
        if (propertyObject != null) {
            List<Property> properties = new ArrayList<>();
            for (int i = 0; i < edgePropertySchema.size(); i++) {
                Property property = new Property();
                JSONObject jsonObject = edgePropertySchema.getJSONObject(i);
                property.setName(jsonObject.getString("name"));
                property.setType(jsonObject.getString("type"));
                property.setValue(propertyObject.getString(jsonObject.getString("name")));
                properties.add(property);
            }
            edgeData.setProperties(JSONObject.toJSONString(properties));
        }
        edgeData.setRank(edgeObject.getLong("rank"));

        // 获取头尾节点数据实体
        String vidType = getVidType(subGraph);
        String srcVid = edgeObject.getString("src");
        NodeData srcNode = getNodeByVid(subGraph, srcVid, vidType, nodePropertySchemaMap);
        edgeData.setSrc(srcNode);
        String dstVid = edgeObject.getString("dst");
        NodeData dstNode = getNodeByVid(subGraph, dstVid, vidType, nodePropertySchemaMap);
        edgeData.setDst(dstNode);

        return edgeData;
    }

    private EdgeData buildEdgeData(String spaceName, JSONObject edgeObject, List<EdgePropertyDTO> edgeProperties, Map<String, List<NodePropertyDTO>> nodePropertiesMap, List<NodeData> nodes,boolean edgeNeedSrcAndDst ) {
        EdgeData edgeData = new EdgeData();
        edgeData.setEdgeType(edgeObject.getString("label_name"));
        JSONObject propertyObject = edgeObject.getJSONObject("properties");
        if (propertyObject != null) {
            List<Property> properties = new ArrayList<>();
            for (int i = 0; i < edgeProperties.size(); i++) {
                Property property = new Property();
                EdgePropertyDTO edgeProperty = edgeProperties.get(i);
                property.setName(edgeProperty.getName());
                property.setType(edgeProperty.getType());
                property.setPrimaryKey(edgeProperty.getPrimaryKey());
                property.setValue(propertyObject.getString(edgeProperty.getName()));
                properties.add(property);
            }
            edgeData.setProperties(properties);
        }
        edgeData.setRank(edgeObject.getLong("rank"));

        // 获取头尾节点数据实体
        if(edgeNeedSrcAndDst) {
            String vidType = getVidType(spaceName);
            String srcVid = edgeObject.getString("src");
            NodeData srcNode = getNodeFromTemp(nodes,srcVid);
            if(srcNode == null) {
                srcNode = getNodeDataByVid(spaceName, srcVid, vidType, nodePropertiesMap);
            }
            edgeData.setSrc(srcNode);
            String dstVid = edgeObject.getString("dst");
            NodeData dstNode = getNodeFromTemp(nodes,dstVid);
            if(dstNode==null) {
                dstNode = getNodeDataByVid(spaceName, dstVid, vidType, nodePropertiesMap);
            }
            edgeData.setDst(dstNode);
        }else {
            String srcVid = edgeObject.getString("src");
            NodeData srcNode = new NodeData();
            srcNode.setVid(srcVid);
            edgeData.setSrc(srcNode);
            String dstVid = edgeObject.getString("dst");
            NodeData dstNode = new NodeData();
            dstNode.setVid(dstVid);
            edgeData.setDst(dstNode);
        }

        return edgeData;
    }

    private NodeData getNodeFromTemp(List<NodeData> nodes,String vid){
        for(NodeData node:nodes){
            if(vid.equals(node.getVid())){
                return node;
            }
        }
        return null;
    }

    /**
     * 生成节点数据实体类
     *
     * @param nodeObject
     * @param nodePropertySchema
     * @return
     */
    private NodeData buildNodeData(JSONObject nodeObject, JSONArray nodePropertySchema) {
        NodeData nodeData = new NodeData();
        nodeData.setVid(nodeObject.getString("identity"));
        nodeData.setNodeType(nodeObject.getString("label"));
        JSONObject propertyObject = nodeObject.getJSONObject("properties");
        List<Property> properties = new ArrayList<>();
        for (int i = 0; i < nodePropertySchema.size(); i++) {
            Property property = new Property();
            JSONObject jsonObject = nodePropertySchema.getJSONObject(i);
            property.setName(jsonObject.getString("name"));
            property.setType(jsonObject.getString("type"));
            property.setValue(propertyObject.getString(jsonObject.getString("name")));
            properties.add(property);
        }
        nodeData.setProperties(JSONObject.toJSONString(properties));
        return nodeData;
    }

    /**
     * 生成节点数据实体类
     *
     * @param nodeObject
     * @param nodeProperties
     * @return
     */
    private NodeData buildNodeData(JSONObject nodeObject, List<NodePropertyDTO> nodeProperties) {
        NodeData nodeData = new NodeData();
        nodeData.setVid(nodeObject.getString("identity"));
        nodeData.setNodeType(nodeObject.getString("label"));
        JSONObject propertyObject = nodeObject.getJSONObject("properties");
        List<Property> properties = new ArrayList<>();
        String nameValue = null;
        for (int i = 0; i < nodeProperties.size(); i++) {
            Property property = new Property();
            NodePropertyDTO nodeProperty = nodeProperties.get(i);
            property.setName(nodeProperty.getName());
            property.setType(nodeProperty.getType());
            property.setPrimaryKey(nodeProperty.getPrimaryKey());
            property.setDisplayField(nodeProperty.getDisplayField());
            property.setValue(propertyObject.getString(nodeProperty.getName()));
            properties.add(property);
            if (nodeProperty.getDisplayField() != null && nodeProperty.getDisplayField()) {
                nameValue = propertyObject.getString(nodeProperty.getName());
            } else if (nameValue == null && nodeProperty.getPrimaryKey() != null && nodeProperty.getPrimaryKey()) {
                nameValue = propertyObject.getString(nodeProperty.getName());
            }
        }
        nodeData.setProperties(properties);
        nodeData.setName(nameValue);
        return nodeData;
    }

    /**
     * 获取属性
     *
     * @param spaceName
     * @param nodeType
     * @return
     */
    protected List<NodePropertyDTO> getNodeProperties(String spaceName, String nodeType) {
        String cypher = "DESC TAG " + nodeType;
        String result = graphTemplate.callCypher(spaceName, cypher);
        List<NodePropertyDTO> resultList = new ArrayList<>();
        if(StringUtils.isNotBlank(result)){
            List<JSONObject> edgeProperties = JSON.parseArray(result, JSONObject.class);
            for (JSONObject edgeProperty : edgeProperties) {
                NodePropertyDTO nodePropertyDTO = new NodePropertyDTO();
                nodePropertyDTO.setName(edgeProperty.getString("Field"));
                nodePropertyDTO.setType(edgeProperty.getString("int64"));
                resultList.add(nodePropertyDTO);
            }
        }
        return resultList;
    }

    private NodePropertyDTO filterNodePropertyByName(List<NodePropertyDTO> properties, String name) {
        for (NodePropertyDTO property : properties) {
            if (property.getName() != null && property.getName().equals(name)) {
                return property;
            }
        }
        return null;
    }

    private EdgePropertyDTO filterEdgePropertyByName(List<EdgePropertyDTO> properties, String name) {
        for (EdgePropertyDTO property : properties) {
            if (property.getName() != null && property.getName().equals(name)) {
                return property;
            }
        }
        return null;
    }

    protected NodePropertyDTO filterPropertyById(List<NodePropertyDTO> properties, Long propertyId) {
        for (NodePropertyDTO property : properties) {
            if (property.getId() != null && property.getId().equals(propertyId)) {
                return property;
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
            return ( (node1.getNodeType()==null && node2.getNodeType() == null || node1.getNodeType() !=null && node1.getNodeType().equals(node2.getNodeType()))
                    && node1.getVid().equals(node2.getVid()));
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

    /**
     * 获取vid类型
     *
     * @param subGraph
     * @return
     */
    protected String getVidType(String subGraph){
        if(graphTemplate instanceof NebulaGraphTemplate) {
            return graphTemplate.getVidType(subGraph);
        }
        return null;
    }

    private NodeData getNodeByVid(String subGraph, String vidVal, String vidType, Map<String, JSONArray> nodePropertieSchemaMap) {
        String nGql;
        if (vidType.equals("INT64")) {
            nGql = "match (v) where id(v) == " + vidVal + " return v;";
        } else {
            nGql = "match (v) where id(v) == \"" + vidVal + "\" return v;";
        }
        String resultStr = graphTemplate.callCypher(subGraph, nGql);
        JSONArray jsonArray = JSON.parseArray(resultStr);
        if (jsonArray.size() > 0) {
            JSONObject jsonObject = jsonArray.getJSONObject(0);
            JSONObject nodeObject = jsonObject.getJSONObject("v");
            String nodeType = nodeObject.getString("label");
            JSONArray nodePropertySchema = nodePropertieSchemaMap.get(nodeType);
            if (nodePropertySchema == null) {
                nodePropertySchema = getNodePropertySchema(subGraph, nodeType);
                nodePropertieSchemaMap.put(nodeType, nodePropertySchema);
            }
            NodeData nodeData = buildNodeData(nodeObject, nodePropertySchema);
            return nodeData;
        }
        return null;
    }

    private NodeData getNodeDataByVid(String spaceName, String vidVal, String vidType, Map<String, List<NodePropertyDTO>> nodePropertiesMap) {
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
            String nodeType = nodeObject.getString("label");
            List<NodePropertyDTO> nodeProperties = nodePropertiesMap.get(nodeType);
            if (nodeProperties == null) {
                nodeProperties = getNodeProperties(spaceName, nodeType);
                nodePropertiesMap.put(nodeType, nodeProperties);
            }
            NodeData nodeData = buildNodeData(nodeObject, nodeProperties);
            return nodeData;
        }
        return null;
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
}
