package com.gientech.raggraphservice.domain.service.impl;

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONArray;
import com.alibaba.fastjson.JSONObject;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.graph.dto.EdgeDTO;
import com.gientech.ragcommon.graph.dto.NodeDTO;
import com.gientech.ragcommon.graph.entity.*;
import com.gientech.ragcommon.graph.enums.GraphEnums;
import com.gientech.ragcommon.graph.enums.GraphFieldEnums;
import com.gientech.ragcommon.graph.request.EdgeSearchRequest;
import com.gientech.ragcommon.graph.request.KeywordSearchRequest;
import com.gientech.ragcommon.graph.request.NodeSearchRequest;
import com.gientech.ragcommon.graph.request.SearchConditionRequest;
import com.gientech.ragcommon.infrastructure.exception.DomainException;
import com.gientech.raggraphservice.domain.service.GraphTemplate;
import com.google.common.collect.Lists;
import com.google.common.collect.Sets;
import jakarta.annotation.Resource;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.collections4.CollectionUtils;
import org.apache.commons.lang3.ObjectUtils;
import org.apache.commons.lang3.StringUtils;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Service;
import java.util.*;
import java.util.stream.Collectors;

@Service
@Slf4j
@ConditionalOnProperty(name = "graph.type", havingValue = "nebula")
public class GraphNebulaQueryDomainServiceImpl extends AbstractGraphQueryDomainService {

    @Resource
    private GraphTemplate graphTemplate;

    @Override
    public GraphData queryNodesByCondition(NodeSearchRequest nodeSearchRequest) throws DomainException {
        try {
            String spaceName = GraphFieldEnums.GRAPH_SPACENAME_PREFIX + nodeSearchRequest.getSpaceName();
            log.info("spaceName:{}", spaceName);
            boolean hasNameCondition = StringUtils.isNotBlank(nodeSearchRequest.getName());
            StringBuilder whereCondition = new StringBuilder();

            List<NodeData> nodes = Lists.newArrayList();
            GraphData graphData = new GraphData();
            whereCondition.delete(0, whereCondition.length());

            if (CollectionUtils.isNotEmpty(nodeSearchRequest.getSearchConditions()) || hasNameCondition) {
                int i = 0;
                if (CollectionUtils.isNotEmpty(nodeSearchRequest.getSearchConditions())) {
                    whereCondition.append("(");
                    for (SearchConditionRequest searchCondition : nodeSearchRequest.getSearchConditions()) {
                        String propertyKey = searchCondition.getPropertyKey();
                        String propertyValue = searchCondition.getPropertyValue();
                        if (i > 0) {
                            whereCondition.append(" ").append(searchCondition.getLogicalOperator()).append(" ");
                        }
                        String operator = "=".equals(searchCondition.getOperator()) ? "==" : searchCondition.getOperator();
                        if ("like".equalsIgnoreCase(operator)) {
                            operator = "CONTAINS";
                        } else if ("not like".equalsIgnoreCase(operator)) {
                            operator = "not CONTAINS";
                        }
                        whereCondition.append("n.").append("`").append(GraphEnums.NODE_TYPE_NAME).append("`").append(".").append("`").append(propertyKey).append("`").append(" ")
                                .append(operator).append(" ").append("'").append(propertyValue).append("'").append(" ");
                        i++;
                    }
                    whereCondition.append(")");
                }
            }

            if(!Objects.isNull(nodeSearchRequest.getFileId())){
                if (whereCondition.length() > 0) {
                    whereCondition.insert(0, " where properties(n).file_id CONTAINS '" + nodeSearchRequest.getFileId() + "' and properties(n).type CONTAINS '" + nodeSearchRequest.getNodeType() + "' and ");
                }else {
                    whereCondition.insert(0, " where properties(n).file_id CONTAINS '" + nodeSearchRequest.getFileId() + "' and properties(n).type CONTAINS '" + nodeSearchRequest.getNodeType() + "' ");
                }
            }else {
                if (whereCondition.length() > 0)
                    whereCondition.insert(0, " where properties(n).type CONTAINS '" + nodeSearchRequest.getNodeType() + "' and ");
                else {
                    whereCondition.insert(0, " where properties(n).type CONTAINS '" + nodeSearchRequest.getNodeType() + "' ");
                }
            }

            StringBuilder nodeCypher = new StringBuilder("match (n:").append("`").append(GraphEnums.NODE_TYPE_NAME).append("`").append(") ")
                    .append(whereCondition).append(" return n limit 500");
            log.info("query cypher:" + nodeCypher);
            String result = graphTemplate.callCypher(spaceName, nodeCypher.toString());
            parseJsonToNodeData(result,nodes);
            graphData.setNodeList(nodes);
            return graphData;
        } catch (Exception e) {
            log.error(e.getMessage(), e);
            throw new DomainException(ErrCodeEnum.EXECUTE_GRAPH_QUERY_ERROR);
        }
    }


    @Override
    public GraphData queryEdgesByCondition(EdgeSearchRequest edgeSearchRequest) throws DomainException {
        try {
            String spaceName = GraphFieldEnums.GRAPH_SPACENAME_PREFIX + edgeSearchRequest.getSpaceName();
            Long fileId = edgeSearchRequest.getFileId();
            String cypherFormat = "match (%s)-[%s]->(%s) %s return %s limit 500;";
            String edgeType = "r"; //可以不选边类型
            String fromNodeType = ""; //可以不选点类型，但只能做id的过滤；要对其他属性过滤需要选择点类型
            String tailNodeType = "";
            StringBuilder whereCondition = new StringBuilder();
            StringBuilder returnClause = new StringBuilder("r");

            //边类型不为空
            if (StringUtils.isNotBlank(edgeSearchRequest.getEdgeType())) {
                edgeType = "r:`" + GraphEnums.EDGE_TYPE_NAME + "`";
                //边条件
                if (CollectionUtils.isNotEmpty(edgeSearchRequest.getEdgePropertiesConditions())) {
                    int i = 0;
                    whereCondition.append("(");
                    for (SearchConditionRequest searchCondition : edgeSearchRequest.getEdgePropertiesConditions()) {
                        String propertyKey = searchCondition.getPropertyKey();
                        String propertyValue = searchCondition.getPropertyValue();
                        if (i > 0) {
                            whereCondition.append(" ").append(searchCondition.getLogicalOperator()).append(" ");
                        }
                        String operator = "=".equals(searchCondition.getOperator()) ? "==" : searchCondition.getOperator();
                        if ("like".equalsIgnoreCase(operator)) {
                            operator = "CONTAINS";
                        } else if ("not like".equalsIgnoreCase(operator)) {
                            operator = "not CONTAINS";
                        }
                        whereCondition.append("r.`").append(propertyKey).append("` ")
                                .append(operator).append(" ").append("'").append(propertyValue).append("'").append(" ");
                        i++;
                    }
                    whereCondition.append(")");
                }
            }

            //处理头节点
            NodeSearchRequest nodeSearchCondition = edgeSearchRequest.getFromNodeSearchRequest();
            boolean hasNameCondition = Objects.nonNull(nodeSearchCondition) && StringUtils.isNotBlank(nodeSearchCondition.getName());
            if (Objects.nonNull(edgeSearchRequest.getFromNodeSearchRequest()) &&
                    StringUtils.isNotBlank(edgeSearchRequest.getFromNodeSearchRequest().getNodeType()) &&
                    CollectionUtils.isNotEmpty(edgeSearchRequest.getFromNodeSearchRequest().getSearchConditions())
                    || hasNameCondition) {

                if (whereCondition.length() > 0) {
                    whereCondition.append(" and ");
                }

                if (Objects.nonNull(edgeSearchRequest.getFromNodeSearchRequest()) &&
                        StringUtils.isNotBlank(edgeSearchRequest.getFromNodeSearchRequest().getNodeType())) {
                    fromNodeType = "n:" + GraphEnums.NODE_TYPE_NAME;
                    returnClause.append(",n");
                    //头节点条件
                    NodeSearchRequest fromNodeCondition = edgeSearchRequest.getFromNodeSearchRequest();
                    if (ObjectUtils.isNotEmpty(fromNodeCondition)
                            && (hasNameCondition || CollectionUtils.isNotEmpty(fromNodeCondition.getSearchConditions()))) {

                        String nodeType = nodeSearchCondition.getNodeType();
                        whereCondition.append("(");
                        if (hasNameCondition) {
//                            whereCondition.append("( n.").append(nodeType).append(".").append(displayProperty.getName())
//                                    .append(" CONTAINS \"").append(nodeSearchCondition.getName()).append("\" ").append(" or ");
//                            whereCondition.append(" id(n) == '" + nodeSearchCondition.getName() + "' )");
                        }

                        if (CollectionUtils.isNotEmpty(nodeSearchCondition.getSearchConditions())) {
                            if (hasNameCondition) {
                                whereCondition.append(" and ");
                            }
                            whereCondition.append("(");
                            int i = 0;
                            for (SearchConditionRequest searchCondition : nodeSearchCondition.getSearchConditions()) {
                                String propertyKey = searchCondition.getPropertyKey();
                                String propertyValue = searchCondition.getPropertyValue();
                                if (i > 0) {
                                    whereCondition.append(" ").append(searchCondition.getLogicalOperator()).append(" ");
                                }
                                String operator = "=".equals(searchCondition.getOperator()) ? "==" : searchCondition.getOperator();
                                if ("like".equalsIgnoreCase(operator)) {
                                    operator = "CONTAINS";
                                } else if ("not like".equalsIgnoreCase(operator)) {
                                    operator = "not CONTAINS";
                                }
                                if (StringUtils.isNotBlank(nodeType)) {
                                    whereCondition.append("n.").append(GraphEnums.NODE_TYPE_NAME).append(".").append(propertyKey).append(" ")
                                            .append(operator).append(" ").append("'").append(propertyValue).append("'").append(" ");
                                } else {
                                    whereCondition.append("properties(n).").append(propertyKey).append(" ")
                                            .append(operator).append("  ").append("'").append(propertyValue).append("'").append(" ");
                                }
                                i++;
                            }
                            whereCondition.append(")");
                        }

                        whereCondition.append(")");
                    }
                } else {
                    //不存在点类型
                    if (hasNameCondition) {
                        returnClause.append(",n");
                        fromNodeType = "n";
                        whereCondition.append("(").append(" id(n) == '" + nodeSearchCondition.getName() + "' ").append(")");

                    }
                }
            }

            //处理尾节点
            nodeSearchCondition = edgeSearchRequest.getTailNodeSearchRequest();
            hasNameCondition = Objects.nonNull(nodeSearchCondition) && StringUtils.isNotBlank(nodeSearchCondition.getName());
            if (Objects.nonNull(nodeSearchCondition) && StringUtils.isNotBlank(edgeSearchRequest.getTailNodeSearchRequest().getNodeType())
                    && CollectionUtils.isNotEmpty(edgeSearchRequest.getTailNodeSearchRequest().getSearchConditions())
                    || hasNameCondition) {

                if (whereCondition.length() > 0) {
                    whereCondition.append(" and ");
                }

                if (Objects.nonNull(nodeSearchCondition) && StringUtils.isNotBlank(edgeSearchRequest.getTailNodeSearchRequest().getNodeType())) {
                    returnClause.append(",m");
                    tailNodeType = "m:" + GraphEnums.NODE_TYPE_NAME;
                    //尾节点条件
                    NodeSearchRequest tailNodeCondition = edgeSearchRequest.getTailNodeSearchRequest();
                    if (ObjectUtils.isNotEmpty(tailNodeCondition)
                            && (hasNameCondition || CollectionUtils.isNotEmpty(tailNodeCondition.getSearchConditions()))) {


                        String nodeType = nodeSearchCondition.getNodeType();
                        whereCondition.append("(");
                        if (CollectionUtils.isNotEmpty(nodeSearchCondition.getSearchConditions())) {
                            if (hasNameCondition) {
                                whereCondition.append(" and ");
                            }
                            whereCondition.append("(");
                            int i = 0;
                            for (SearchConditionRequest searchCondition : nodeSearchCondition.getSearchConditions()) {
                                String propertyKey = searchCondition.getPropertyKey();
                                String propertyValue = searchCondition.getPropertyValue();
                                if (i > 0) {
                                    whereCondition.append(" ").append(searchCondition.getLogicalOperator()).append(" ");
                                }
                                String operator = "=".equals(searchCondition.getOperator()) ? "==" : searchCondition.getOperator();
                                if ("like".equalsIgnoreCase(operator)) {
                                    operator = "CONTAINS";
                                } else if ("not like".equalsIgnoreCase(operator)) {
                                    operator = "not CONTAINS";
                                }
                                if (StringUtils.isNotBlank(nodeType)) {
                                    whereCondition.append("m.").append(GraphEnums.NODE_TYPE_NAME).append(".").append(propertyKey).append(" ")
                                            .append(operator).append(" ").append("'").append(propertyValue).append("'").append(" ");
                                } else {
                                    whereCondition.append("properties(m).").append(propertyKey).append(" ")
                                            .append(operator).append(" ").append("'").append(propertyValue).append("'").append(" ");
                                }
                                i++;
                            }
                            whereCondition.append(")");
                        }
                        whereCondition.append(")");
                    }
                } else {
                    if (hasNameCondition) {
                        returnClause.append(",m");
                        tailNodeType = "m";
                        if (whereCondition.length() > 0) {
                            whereCondition.append(" and ");
                        }
                        whereCondition.append("(").append(" id(m) == '" + nodeSearchCondition.getName() + "' ").append(")");
                    }
                }
            }

            if(!Objects.isNull(fileId)){
                if (whereCondition.length() > 0) {
                    whereCondition.insert(0, " where properties(r).show_flag=='1' and properties(r).file_id CONTAINS '" + fileId + "' and properties(r).name CONTAINS '" + edgeSearchRequest.getEdgeType() + "' and ");
                }else {
                    whereCondition.insert(0, " where properties(r).show_flag=='1' and properties(r).file_id CONTAINS '" + fileId + "' and properties(r).name CONTAINS '" + edgeSearchRequest.getEdgeType() + "' ");
                }
            }else {
                if (whereCondition.length() > 0)
                    whereCondition.insert(0, " where properties(r).show_flag=='1' and properties(r).name CONTAINS '" + edgeSearchRequest.getEdgeType() + "' and ");
                else
                    whereCondition.insert(0, " where properties(r).show_flag=='1' and properties(r).name CONTAINS '" + edgeSearchRequest.getEdgeType() + "' ");
            }

            String cypher = String.format(cypherFormat, fromNodeType, edgeType, tailNodeType, whereCondition, returnClause);
            log.info("query cypher:" + cypher);
            String resultJSON = graphTemplate.callCypher(spaceName, cypher);
            GraphData graphData = parseJsonToGraphData(spaceName,resultJSON);
            // 去除只有尾节点的悬空边
            if (CollectionUtils.isNotEmpty(graphData.getEdgeList())) {
                graphData.setEdgeList(graphData.getEdgeList().stream().filter(e -> Objects.nonNull(e.getSrc())).collect(Collectors.toList()));
            }
            if (CollectionUtils.isEmpty(graphData.getNodeList()) && CollectionUtils.isNotEmpty(graphData.getEdgeList())) {
                Set<NodeData> nodes = Sets.newHashSet();
                for (EdgeData edgeData : graphData.getEdgeList()) {
                    if (edgeData.getSrc() != null) {//有可能存在悬空节点
                        nodes.add(edgeData.getSrc());
                    }
                    if (edgeData.getDst() != null) {//有可能存在悬空节点
                        nodes.add(edgeData.getDst());
                    }
                }
                graphData.setNodeList(new ArrayList<>(nodes));
            }
            return graphData;
        } catch (Exception e) {
            throw new DomainException(ErrCodeEnum.EXECUTE_GRAPH_QUERY_ERROR, e);
        }
    }

    /**
     * 根据点查边
     *
     * @param spaceName
     * @param graphData
     * @return
     */
    @Override
    protected GraphData getEdgesFromData(String spaceName, GraphData graphData) {
        String vidType = getVidType(spaceName);
        StringBuilder edgeCypher = new StringBuilder("match (n)-[r]-(m) where id(n) in [");
        for (int i = 0; i < graphData.getNodeList().size(); i++) {
            if (i > 0) {
                edgeCypher.append(",");
            }
            if (vidType.contains("INT")) {
                edgeCypher.append(graphData.getNodeList().get(i).getVid());
            } else {
                edgeCypher.append("\"").append(graphData.getNodeList().get(i).getVid()).append("\"");
            }
        }
        edgeCypher.append("] return r,m");
        String edgeResultStr = graphTemplate.callCypher(spaceName, edgeCypher.toString());
        GraphData subGraph = parseJsonToGraphData(spaceName, edgeResultStr);
        return subGraph;
    }

    /**
     * 获取vid类型
     *
     * @param subGraph
     * @return
     */
    @Override
    protected String getVidType(String subGraph) {
        return graphTemplate.getVidType(subGraph);
    }

    @Override
    public List<Keyword> keywordSearch(KeywordSearchRequest keywordSearch) {
        String spaceName = GraphFieldEnums.GRAPH_SPACENAME_PREFIX + keywordSearch.getSpaceName();
        String nodeType = keywordSearch.getNodeType();
        String key = keywordSearch.getKeyword();
        StringBuilder nodeCypher = new StringBuilder("match (n:`");
        nodeCypher.append(nodeType).append("`) ");
        //查询条件
        if (!StringUtils.isEmpty(key)) {
            //需要对字符进行转义
            String keyword = escapeSpecialChars(key);
            StringBuilder whereCondition = new StringBuilder();
            whereCondition.append("where id(n) contains ");
            whereCondition.append("'").append(keyword).append("'");
            nodeCypher.append(whereCondition);
        }
        //返回的字段
        nodeCypher.append(" return n ");
        nodeCypher.append(" limit 50 ");
        String result = graphTemplate.callCypher(spaceName, nodeCypher.toString());
        JSONArray resultObj = JSON.parseArray(result);
        List<Keyword> resultKeys = new ArrayList<>();
        resultObj.stream().forEach(o -> {
            JSONObject json = (JSONObject) o;
            JSONObject dataJson = json.getJSONObject("n");
            resultKeys.add(new Keyword(dataJson.getString("identity"),dataJson.getString("label"),dataJson.getJSONObject("properties")));
        });
        return resultKeys;
    }

    private static String escapeSpecialChars(String input) {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < input.length(); i++) {
            char c = input.charAt(i);

            if (c == '"') {
                sb.append('\\').append('"'); // 转义双引号
            } else if (c == '\'') {
                sb.append('\\').append('\''); // 转义单引号
            } else if (c == '\\') {
                sb.append('\\').append('\\'); // 转义反斜线
            } else if (c == '\n') {
                sb.append('\\').append('n'); // 转义换行符
            } else if (c == '\t') {
                sb.append('\\').append('t'); // 转义制表符
            } else if (c == '\r') {
                sb.append('\\').append('r'); // 转义回车符
            } else {
                sb.append(c); // 不需要转义的字符直接添加到结果字符串中
            }
        }
        return sb.toString();
    }

    @Override
    public List<GraphInstance> instance(String spaceName, List<Long> fileIds) {
        String cypher;
        List<GraphInstance> graphInstances = Lists.newArrayList();
        //查询图空间下的所有的点和边的数据
        if(CollectionUtils.isEmpty(fileIds)){
            GraphInstance graphInstance = new GraphInstance();
            //查询点实例数
            cypher = "MATCH (v) return count(v) as count";
            graphInstance.setNodeCount(getTagOrEdgeInstance(spaceName,cypher,null));
            //查询边实例数
            cypher = "MATCH ()-[e:" + GraphEnums.EDGE_TYPE_NAME + "]->() where properties(e).show_flag=='1' return count(e) as count";
            graphInstance.setEdgeCount(getTagOrEdgeInstance(spaceName,cypher,null));
            graphInstances.add(graphInstance);
            return graphInstances;
        }
        //查询某个文件下的点和边的实例数据
        for (Long fileId : fileIds) {
            GraphInstance graphInstance = new GraphInstance();
            //查询点实例数
            cypher = "MATCH (v) where properties(v).file_id CONTAINS '%d' return count(v) as count";
            graphInstance.setNodeCount(getTagOrEdgeInstance(spaceName,cypher,fileId));
            //查询边实例数
            cypher = "MATCH ()-[e:" + GraphEnums.EDGE_TYPE_NAME + "]->() where properties(e).show_flag=='1' and properties(e).file_id CONTAINS '%d'  return count(e) as count";
            graphInstance.setEdgeCount(getTagOrEdgeInstance(spaceName,cypher,fileId));
            graphInstance.setFileId(fileId);
            graphInstances.add(graphInstance);
        }
        return graphInstances;
    }

    private Integer getTagOrEdgeInstance(String spaceName, String cypher, Long fileId) {
        Integer count = 0;
        if(Objects.nonNull(fileId))
            cypher = String.format(cypher,fileId);
        String result = graphTemplate.callCypher(spaceName, cypher);
        if(StringUtils.isNotBlank(result)){
            List<JSONObject> data = JSONArray.parseArray(result, JSONObject.class);
            count = data.get(0).getInteger("count");
        }
        return count;
    }

    @Override
    public List<String> nodes(String spaceName) {
        String cypher = "SHOW tags";
        return getTagsOrEdgs(spaceName,cypher);
    }

    @Override
    public List<NodeDTO.NodeProperty>  nodeProperties(String spaceName, String nodeType) {
        String cypher = "DESCRIBE TAG " + nodeType;
        String result = graphTemplate.callCypher(spaceName, cypher);
        List<NodeDTO.NodeProperty> nodeProperties = Lists.newArrayList();
        if(StringUtils.isNotBlank(result)){
            List<JSONObject> datas = JSONArray.parseArray(result, JSONObject.class);
            datas.forEach(data -> {
                NodeDTO.NodeProperty nodeProperty = new NodeDTO.NodeProperty();
                nodeProperty.setPropertyName(data.getString("Field"));
                nodeProperty.setPropertyType(data.getString("Type"));
                nodeProperties.add(nodeProperty);
            });
        }
        return nodeProperties;
    }

    @Override
    public List<String> edges(String spaceName) {
        String cypher = "SHOW edges";
        return getTagsOrEdgs(spaceName,cypher);
    }

    @Override
    public List<EdgeDTO.EdgeProperty> edgeProperties(String spaceName, String edgeType) {
        String cypher = "DESCRIBE EDGE " + edgeType;
        String result = graphTemplate.callCypher(spaceName, cypher);
        List<EdgeDTO.EdgeProperty> edgeProperties = Lists.newArrayList();
        if(StringUtils.isNotBlank(result)){
            List<JSONObject> datas = JSONArray.parseArray(result, JSONObject.class);
            datas.forEach(data -> {
                EdgeDTO.EdgeProperty nodeProperty = new EdgeDTO.EdgeProperty();
                nodeProperty.setPropertyName(data.getString("Field"));
                nodeProperty.setPropertyType(data.getString("Type"));
                edgeProperties.add(nodeProperty);
            });
        }
        return edgeProperties;
    }

    private List<String> getTagsOrEdgs(String spaceName,String cypher) {
        List<String> resultList = Lists.newArrayList();
        String result = graphTemplate.callCypher(spaceName, cypher);
        if(StringUtils.isEmpty(result))
            return resultList;
        List<JSONObject> jsonDatas = JSONObject.parseArray(result, JSONObject.class);
        jsonDatas.forEach(json -> resultList.add(json.getString("Name")));
        return resultList;
    }

    @Override
    public Set<String> nodeTypes(String spaceName,String nodeType,Long fileId) {
        StringBuilder cypher = new StringBuilder("MATCH (v:").append(nodeType).append(") ");
        if(!Objects.isNull(fileId))
            cypher.append(" WHERE properties(v).file_id CONTAINS '").append(fileId).append("' ");
        cypher.append("RETURN  properties(v).type AS types,size(collect(properties(v).type))");
        String result = graphTemplate.callCypher(spaceName, cypher.toString());
        Set<String> nodeTypeSet= Sets.newHashSet();
        if(StringUtils.isNotBlank(result)){
            List<JSONObject> nodeTypes = JSON.parseArray(result,JSONObject.class);
            nodeTypes.forEach(tyep ->{
                String types = tyep.getString("types");
                nodeTypeSet.addAll(Lists.newArrayList(types.split(",")));
            });
        }
        return nodeTypeSet;
    }

    @Override
    public Set<String> edgeTypes(String spaceName, String edgeType, Long fileId) {
        // MATCH ()-[e:relationship]-()  WHERE properties(e).file_id CONTAINS '53873'  RETURN  properties(e).name AS types,size(collect(properties(e).type))
        StringBuilder cypher = new StringBuilder("MATCH ()-[e:").append(edgeType).append("]-() ");
        if(!Objects.isNull(fileId))
            cypher.append("WHERE properties(e).file_id CONTAINS '").append(fileId).append("' ");
        cypher.append(" RETURN  properties(e).name AS types,size(collect(properties(e).type))");
        String result = graphTemplate.callCypher(spaceName, cypher.toString());
        Set<String> edgeSet = Sets.newHashSet();
        if(StringUtils.isNotBlank(result)){
            List<JSONObject> edgeTypes = JSON.parseArray(result,JSONObject.class);
            edgeTypes.forEach(tyep -> edgeSet.add(tyep.getString("types")));
        }
        return edgeSet;
    }

    @Override
    public GraphData searchByFile(String spaceName, Long fileId, Integer pageNum) {
        String cypher = "MATCH (src)-[e:" + GraphEnums.EDGE_TYPE_NAME + "]->(dst) where properties(e).show_flag=='1' and properties(e).file_id CONTAINS '" + fileId + "'  and properties(e).page_num CONTAINS '" + fileId + "_" + pageNum + "'   return e,src,dst ";
//        String cypher = "MATCH (src)-[e:" + GraphEnums.EDGE_TYPE_NAME + "]->(dst) where properties(e).show_flag=='1' and properties(e).file_id CONTAINS '" + fileId + "'   return e,src,dst ";
        String result = graphTemplate.callCypher(spaceName, cypher);
        if(StringUtils.isEmpty(result))
            return null;
        List<JSONObject> resultJson = JSON.parseArray(result, JSONObject.class);
        GraphData graphData = new GraphData();
        List<EdgeData> edgeList = Lists.newArrayList();
        List<NodeData> nodeList = Lists.newArrayList();
        graphData.setEdgeList(edgeList);
        graphData.setNodeList(nodeList);
        resultJson.forEach(item -> {
            JSONObject edge = item.getJSONObject("e");
            JSONObject src = item.getJSONObject("src");
            JSONObject dst = item.getJSONObject("dst");

            //src
            NodeData srcNodeData = new NodeData();
            JSONObject srcProperties = src.getJSONObject("properties");
            srcNodeData.setVid(src.getString("identity"));
            srcNodeData.setNodeType(srcProperties.getString("type"));
            srcNodeData.setName(srcProperties.getString("name"));
            srcNodeData.setProperties(srcProperties);

            //dst
            NodeData dstNodeData = new NodeData();
            JSONObject dstProperties = dst.getJSONObject("properties");
            dstNodeData.setVid(dst.getString("identity"));
            dstNodeData.setNodeType(dstProperties.getString("type"));
            dstNodeData.setName(dstProperties.getString("name"));
            dstNodeData.setProperties(dstProperties);

            //edge
            EdgeData edgeData = new EdgeData();
            JSONObject edgeProperties = edge.getJSONObject("properties");
            edgeData.setEdgeType(edgeProperties.getString("name"));
            edgeData.setProperties(edgeProperties);
            edgeData.setName(edgeProperties.getString("name"));
            edgeData.setRank(edge.getLong("rank"));
            edgeData.setSrc(srcNodeData);
            edgeData.setDst(dstNodeData);

            nodeList.add(srcNodeData);
            nodeList.add(dstNodeData);
            edgeList.add(edgeData);
        });
        return graphData;
    }
}
