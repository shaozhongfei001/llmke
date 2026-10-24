package com.gientech.raggraphservice.application.service.impl;

import cn.hutool.core.bean.BeanUtil;
import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONArray;
import com.alibaba.fastjson.JSONObject;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.graph.dto.*;
import com.gientech.ragcommon.graph.entity.*;
import com.gientech.ragcommon.graph.enums.GraphEnums;
import com.gientech.ragcommon.graph.enums.GraphFieldEnums;
import com.gientech.ragcommon.graph.enums.PathSearchType;
import com.gientech.ragcommon.graph.enums.SearchDirectionEnum;
import com.gientech.ragcommon.graph.request.*;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.raggraphservice.application.service.*;
import com.gientech.raggraphservice.domain.service.GraphQueryDomainService;
import com.gientech.raggraphservice.domain.service.GraphTemplate;
import com.gientech.raggraphservice.infrastructure.GraphDataParser;
import com.gientech.start.redisson.utils.RedissonUtils;
import com.google.common.collect.Lists;
import com.google.common.collect.Maps;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.collections4.CollectionUtils;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.stream.Collectors;

import static com.gientech.ragcommon.infrastructure.emuns.RedisKeyEnums.SUB_GRAPH_PREFIX;


@Service
@Slf4j
@ConditionalOnProperty(name = "graph.type", havingValue = "nebula")
public class GraphNebulaSearchAppServiceImpl implements GraphSearchAppService {

    @Autowired
    private GraphTemplate graphTemplate;

    @Autowired
    private GraphDataParser graphDataParser;

    @Autowired
    private RedissonUtils redissonUtils;

    @Autowired
    private GraphQueryDomainService graphQueryDomainService;


    @Override
    public GraphDataDTO searchNodeOneStep(NodeStepSearchRequest nodeStepSearchRequest) {
        String spaceName = GraphFieldEnums.GRAPH_SPACENAME_PREFIX + nodeStepSearchRequest.getSpaceName();
        Long fileId = nodeStepSearchRequest.getFileId();
        List<String> vids = Lists.newArrayList();

        //1.获取vids
        if (CollectionUtils.isEmpty(nodeStepSearchRequest.getNodes())) {
            throw new ApplicationException("要查询的节点为空");
        }
        for (NodeDataDTO nodeDataDTO : nodeStepSearchRequest.getNodes()) {
            Optional<NebulaNodeResult> node;
            try {
                //主键类型一定为String
                String resultJSON = graphTemplate.callCypher(spaceName, String.format("match (v) where id(v) == '%s' return v limit 500 ", nodeDataDTO.getVid()));
                node = JSONArray.parseArray(resultJSON, NebulaNodeResult.class).stream().findFirst();
            } catch (Exception ex) {
                log.error(ex.getMessage(), ex);
                throw new ApplicationException(ex.getMessage());
            }
            if (!node.isPresent())
                throw new ApplicationException("节点不存在");
            vids.add(node.get().getV().getIdentity());
        }
        try {
            String cypher;
            if(!Objects.isNull(fileId)){
                cypher = String.format("GO %d STEPS FROM %s OVER " + GraphEnums.EDGE_TYPE_NAME + " bidirect where properties(edge).file_id CONTAINS '%d' and properties(edge).show_flag=='1' YIELD edge as e, src(edge) as src, dst(edge) as dst | limit 500;", nodeStepSearchRequest.getStep(), vids.stream().map(i -> "'" + i + "'").collect(Collectors.joining(",")),fileId);
            }else
                cypher = String.format("GO %d STEPS FROM %s OVER " + GraphEnums.EDGE_TYPE_NAME + " bidirect where properties(edge).show_flag=='1' YIELD edge as e, src(edge) as src, dst(edge) as dst | limit 500;", nodeStepSearchRequest.getStep(), vids.stream().map(i -> "'" + i + "'").collect(Collectors.joining(",")));
            String resultJSON = graphTemplate.callCypher(spaceName, cypher);
            log.info("resultJSON:{}", resultJSON);
            return buildGraphData(resultJSON, spaceName);
        } catch (Exception ex) {
            ex.printStackTrace();
            log.error(ex.getMessage());
            throw new ApplicationException(ErrCodeEnum.EXECUTE_GRAPH_QUERY_ERROR.getErrCode(), ex.getMessage());
        }

    }

    @Override
    public GraphDataDTO wholeGraphSearch(WholeGraphSearchRequest wholeGraphSearchRequest)  {
        String sapceName = GraphFieldEnums.GRAPH_SPACENAME_PREFIX + wholeGraphSearchRequest.getSpaceName();
        try {
            //查询边
            String cypher = null;
            if(Objects.nonNull(wholeGraphSearchRequest.getFileId()))
                cypher = String.format("match ()-[e:" + GraphEnums.EDGE_TYPE_NAME + "]->() where properties(e).file_id CONTAINS '%d' and properties(e).show_flag=='1' return e limit %d",wholeGraphSearchRequest.getFileId(),wholeGraphSearchRequest.getLimit());
            else
                cypher = String.format("match ()-[e:" + GraphEnums.EDGE_TYPE_NAME + "]->() where properties(e).show_flag=='1' return e limit %d", wholeGraphSearchRequest.getLimit());
            log.info("查询边cypher语句:{}",cypher);
            String edgeResult = graphTemplate.callCypher(sapceName, cypher);
            log.info("查询边结果:{}",edgeResult);
            List<JSONObject> edgeJsons = JSON.parseArray(edgeResult, JSONObject.class);

            //查询点
            if(Objects.nonNull(wholeGraphSearchRequest.getFileId()))
                cypher = String.format("match (v) where properties(v).file_id CONTAINS '%d' return v limit %d",wholeGraphSearchRequest.getFileId(),wholeGraphSearchRequest.getLimit());
            else
                cypher = String.format("match (v) return v limit %d", wholeGraphSearchRequest.getLimit());
            log.info("查询点cypher语句:{}",cypher);
            String nodeResult = graphTemplate.callCypher(sapceName, cypher);
            log.info("查询点结果:{}",nodeResult);
            List<JSONObject> nodeJsons = JSON.parseArray(nodeResult, JSONObject.class);
            return buildGraphResult(edgeJsons, nodeJsons);
        } catch (Exception ex) {
            ex.printStackTrace();
            log.error(ex.getMessage());
            return null;
        }

    }

    private GraphDataDTO buildGraphResult(List<JSONObject> edgeJsons, List<JSONObject> nodeJsons) {
        GraphDataDTO graphDataDTO = new GraphDataDTO();
        List<NodeDataDTO> nodeList = Lists.newArrayList();
        Map<String,NodeDataDTO> nodeMap = Maps.newHashMap();
        //处理点数据
        nodeJsons.forEach(nodeJson -> {
            JSONObject node = nodeJson.getJSONObject("v");
            JSONObject properties = node.getJSONObject("properties");
            NodeDataDTO nodeDataDTO = new NodeDataDTO();
            nodeDataDTO.setVid(node.getString("identity"));
            nodeDataDTO.setName(properties.getString("name"));
            nodeDataDTO.setNodeType(properties.getString("type"));
            nodeDataDTO.setProperties(properties);
            nodeMap.put(nodeDataDTO.getVid(),nodeDataDTO);
            nodeList.add(nodeDataDTO);
        });

        //处理边数据
        List<EdgeDataDTO> edgeList = Lists.newArrayList();
        edgeJsons.forEach(edgeJson -> {
            JSONObject edge = edgeJson.getJSONObject("e");
            JSONObject properties = edge.getJSONObject("properties");
            EdgeDataDTO edgeDataDTO = new EdgeDataDTO();
            edgeDataDTO.setEdgeType(properties.getString("name"));
            edgeDataDTO.setSrc(nodeMap.get(edge.getString("src")));
            edgeDataDTO.setDst(nodeMap.get(edge.getString("dst")));
            edgeDataDTO.setName(properties.getString("name"));
            edgeDataDTO.setRank(edge.getLong("rank"));
            edgeList.add(edgeDataDTO);
        });
        graphDataDTO.setNodeList(nodeList);
        graphDataDTO.setEdgeList(edgeList);
        return graphDataDTO;
    }

    @Override
    public Boolean canSearchNodeOneStep(String spaceName, String nodeType, String nodeInstanceId) throws ApplicationException {
        String cypher = String.format("match (v:%s)-[r]-() where id(v) == \"%s\" return r limit 1", nodeType, nodeInstanceId);
        String resultStr = graphTemplate.callCypher(spaceName, cypher);
        JSONArray jsonArray = JSON.parseArray(resultStr);
        if (jsonArray != null && jsonArray.size() > 0) {
            return true;
        }
        return false;
    }

    @Override
    public List<PathDTO> pathSearch(PathSearchRequest pathSearchRequest) throws Exception {
        String spaceName = GraphFieldEnums.GRAPH_SPACENAME_PREFIX + pathSearchRequest.getSpaceName();
        StringBuilder whereClause = new StringBuilder();
        if (CollectionUtils.isNotEmpty(pathSearchRequest.getConditions())) {
            whereClause.append("WHERE");
            for (EdgeSearchRequest edgeSearch : pathSearchRequest.getConditions()) {
                if (edgeSearch.getEdgePropertiesConditions().stream().findFirst().isPresent()) {
                    for (SearchConditionRequest condition : edgeSearch.getEdgePropertiesConditions()) {
                        whereClause.append("(").append(edgeSearch.getEdgeType()).append(".").append(condition.getPropertyName()).append(" IS EMPTY ").append("OR ");
                        whereClause.append(" AND ");
                    }
                }
            }
            whereClause.delete(whereClause.length() - 5, whereClause.length());
        }

        //direction
        SearchDirectionEnum directionEnum = SearchDirectionEnum.of(pathSearchRequest.getDirection());
        String direction = "";
        switch (directionEnum) {
            case OUTGOING:
                break;
            case INCOMING:
                //交换节点
                NodeDataDTO temp = pathSearchRequest.getFromNode();
                pathSearchRequest.setFromNode(pathSearchRequest.getTailNode());
                pathSearchRequest.setTailNode(temp);
                break;
            case BIDIRECT:
                direction = directionEnum.getDirection();
                break;
        }
        String stepCondition = "";
        if (Objects.nonNull(pathSearchRequest.getStep())) {
            stepCondition = "UPTO " + pathSearchRequest.getStep() + " STEPS ";
        }
        String edgeTypes = CollectionUtils.isEmpty(pathSearchRequest.getEdgeTypes()) ? "*" : pathSearchRequest.getEdgeTypes().stream().collect(Collectors.joining(","));//如果边类别为空则查出所有的
        try {
            String resultJSON = graphTemplate.callCypher(spaceName, String.format("FIND %s PATH FROM '%s' TO '%s' OVER %s %s %s %s YIELD path as p | limit 500;",
                    PathSearchType.of(pathSearchRequest.getSearchType()).getType(), pathSearchRequest.getFromNode().getVid(), pathSearchRequest.getTailNode().getVid(),
                    edgeTypes, direction, whereClause, stepCondition));
            List<PathDataDTO> paths = JSONArray.parseArray(resultJSON, PathDataDTO.class);

            //点过滤（要经过哪些节点）
            paths = filterPathByNodeTypes(paths, pathSearchRequest, spaceName);

            List<PathDTO> results = new ArrayList<>();
            for (PathDataDTO row : paths) {
                if (row.getP() != null) {
                    results.addAll(row.getP());
                }
            }
            //设一下id
            for (int i = 0; i < results.size(); i++) {
                PathDTO path = results.get(i);
                path.setId((long) (i + 1));
            }

            return results;
        } catch (Exception ex) {
            log.error(ex.getMessage(), ex);
            throw new ApplicationException(ex.getMessage());
        }


    }

    private List<PathDataDTO> filterPathByNodeTypes(List<PathDataDTO> paths, PathSearchRequest searchRequest, String ontologyName) {
        List<PathDataDTO> filteredPaths = Lists.newArrayList();
        //{k:vid,v:NodeDataDTO}
        Map<String, NodeDataDTO> nodeDataMap = new HashMap<>();
        for (PathDataDTO path : paths) {
            boolean flag = false;
            for (PathDTO pathDTO : path.getP()) {
                //首尾节点不在过滤范围内

                //针对反向路径
                if (pathDTO.getBriefPath().contains("<")) {
                    pathDTO.setStartNode(pathDTO.getEndNode());
                }

                for (NodeDataDTO node : pathDTO.getNodes()) {
                    String nebulaNode = graphTemplate.callCypher(ontologyName, String.format("match (v) where id(v) == '%s' return v;", node.getVid()));
                    Optional<NebulaNodeResult> first = JSONArray.parseArray(nebulaNode, NebulaNodeResult.class).stream().findFirst();
                    if (first.isPresent()) {
                        Object name = first.get().getV().getProperties().get("name");
                        if (Objects.nonNull(name)) {
                            node.setName((String) name);
                        } else {
                            node.setName(node.getVid());
                        }
                        node.setNodeType(first.get().getV().getLabel());
                        node.setProperties(JSONObject.parseObject(JSONObject.toJSONString(first.get().getV().getProperties()),JSONObject.class));

                        nodeDataMap.put(node.getVid(), node);
                    }
                }
            }
            if (!flag) {
                filteredPaths.add(path);
            }
        }
        for (PathDataDTO path : filteredPaths) {
            for (PathDTO pathDTO : path.getP()) {
                for (EdgeDataDTO edge : pathDTO.getEdges()) {
                    String edgeJson = graphTemplate.callCypher(ontologyName, String.format("match (v1)-[e]->(v2) where id(v1) == '%s' and id(v2) == '%s' return e;", edge.getSrc().getVid(), edge.getDst().getVid()));
                    Optional<NebulaEdgeResult> first = JSONObject.parseArray(edgeJson, NebulaEdgeResult.class).stream().findFirst();
                    if (first.isPresent()) {
                        Object name = first.get().getE().getProperties().get("name");
                        if (Objects.nonNull(name)) {
                            edge.setName((String) name);
                        }
                        NebulaEdge nebulaEdge = first.get().getE();

                        edge.setProperties(JSONObject.parseObject(JSONObject.toJSONString(nebulaEdge.getProperties())));
                        NodeDataDTO srcNode = nodeDataMap.get(nebulaEdge.getSrc());
                        NodeDataDTO dstNode = nodeDataMap.get(nebulaEdge.getDst());
                        edge.setSrc(srcNode);
                        edge.setDst(dstNode);
                    }
                }
            }
        }
        return filteredPaths;
    }

    @Override
    public List<NeighbourNodeDTO> commonNeighbourSearch(CommonNeighbourRequest commonNeighbourRequest) throws ApplicationException {
        String spaceName = GraphFieldEnums.GRAPH_SPACENAME_PREFIX + commonNeighbourRequest.getSpaceName();
        String vid1 = commonNeighbourRequest.getNodeInstanceId1();
        String vid2 = commonNeighbourRequest.getNodeInstanceId2();

        Set<String> neighbourVids = new HashSet<>();
        String edgeTypeFilter = neighbourSearchOfEdgeTypes(commonNeighbourRequest.getEdgeTypes());

        // 1) node1 -> neighbour -> node2
        String nodeFilter = neighbourSearchOfNodeFilter(commonNeighbourRequest.getNodeSearchRequests(), "dst(EDGE)");
        String cypher = String.format("GO FROM \"%s\" OVER %s %s YIELD dst(EDGE) AS neighbor | GO FROM $-.neighbor OVER %s WHERE dst(edge) == \"%s\" YIELD $-.neighbor | limit 500;",
                vid1, edgeTypeFilter, nodeFilter, edgeTypeFilter, vid2);
        String resultStr = graphTemplate.callCypher(spaceName, cypher);
        collectNeighbourVids(neighbourVids, resultStr, vid1, vid2);

        // 2) node1 -> neighbour <- node2
        nodeFilter = neighbourSearchOfNodeFilter(commonNeighbourRequest.getNodeSearchRequests(), "dst(EDGE)");
        cypher = String.format("GO FROM \"%s\" OVER %s %s YIELD dst(EDGE) AS neighbor | GO FROM $-.neighbor OVER %s REVERSELY WHERE src(edge) == \"%s\" YIELD $-.neighbor | limit 500;",
                vid1, edgeTypeFilter, nodeFilter, edgeTypeFilter, vid2);
        resultStr = graphTemplate.callCypher(spaceName, cypher);
        collectNeighbourVids(neighbourVids, resultStr, vid1, vid2);

        // 3) node1 <- neighbour -> node2
        nodeFilter = neighbourSearchOfNodeFilter(commonNeighbourRequest.getNodeSearchRequests(), "src(EDGE)");
        cypher = String.format("GO FROM \"%s\" OVER %s REVERSELY %s YIELD src(EDGE) AS neighbor | GO FROM $-.neighbor OVER %s WHERE dst(edge) == \"%s\" YIELD $-.neighbor | limit 500;",
                vid1, edgeTypeFilter, nodeFilter, edgeTypeFilter, vid2);
        resultStr = graphTemplate.callCypher(spaceName, cypher);
        collectNeighbourVids(neighbourVids, resultStr, vid1, vid2);

        // 4) node1 <- neighbour <- node2
        nodeFilter = neighbourSearchOfNodeFilter(commonNeighbourRequest.getNodeSearchRequests(), "src(EDGE)");
        cypher = String.format("GO FROM \"%s\" OVER %s REVERSELY %s YIELD src(EDGE) AS neighbor | GO FROM $-.neighbor OVER %s REVERSELY WHERE src(edge) == \"%s\" YIELD $-.neighbor | limit 500;",
                vid1, edgeTypeFilter, nodeFilter, edgeTypeFilter, vid2);
        resultStr = graphTemplate.callCypher(spaceName, cypher);
        collectNeighbourVids(neighbourVids, resultStr, vid1, vid2);

        if (CollectionUtils.isNotEmpty(neighbourVids)) {
            List<NeighbourNodeDTO> result = new ArrayList<>();
            Map<String, JSONObject> nodePropertiesMap = new HashMap<>();
            Map<String, JSONObject> edgePropertiesMap = new HashMap<>();

            for (String vid : neighbourVids) {
                // 获取邻居节点信息
                String nodeCypher = String.format("match (v) where id(v) == \"%s\" return v limit 500;", vid);
                String nodeStr = graphTemplate.callCypher(spaceName, nodeCypher);
                JSONObject nodeObject = JSON.parseArray(nodeStr).getJSONObject(0).getJSONObject("v");
                String nodeType = nodeObject.getString("label");
                JSONObject nodeProperties = nodePropertiesMap.get(nodeType);
                if (nodeProperties == null) {
//                    nodeProperties = getNodeProperties(spaceName, nodeType);
                    nodePropertiesMap.put(nodeType, nodeObject.getJSONObject("properties"));
                }
                NeighbourNodeDTO node = buildNeighbourNodeDTO(nodeObject);

                // 获取邻居节点关联的边
                List<EdgeDataDTO> edges = new ArrayList<>();
                String edgeCypher = String.format("match (n)-[r]-(m) where id(n) == \"%s\" and (id(m) == \"%s\" or id(m) == \"%s\") return r limit 500;", vid, vid1, vid2);
                String edgeStr = graphTemplate.callCypher(spaceName, edgeCypher);
                JSONArray jsonArray = JSON.parseArray(edgeStr);
                for (int i = 0; i < jsonArray.size(); i++) {
                    JSONObject jsonObject = jsonArray.getJSONObject(i);
                    JSONObject edgeObject = jsonObject.getJSONObject("r");
                    String edgeType = edgeObject.getString("label_name");
                    JSONObject edgeProperties = edgePropertiesMap.get(edgeType);
                    if (edgeProperties == null) {
//                        edgeProperties = getEdgeProperties(spaceName, edgeType);
                        edgePropertiesMap.put(edgeType, edgeObject.getJSONObject("properties"));
                    }
                    EdgeDataDTO edge = buildEdgeDataDTO(spaceName, spaceName, edgeObject, edgeProperties, nodePropertiesMap);
                    List<NodeDataDTO> nodeDataDTOList = Lists.newArrayList();
                    if (Objects.nonNull(edge.getSrc())) {
                        nodeDataDTOList.add(edge.getSrc());
                    }
                    if (Objects.nonNull(edge.getDst())) {
                        nodeDataDTOList.add(edge.getDst());
                    }
                    edges.add(edge);
                }
                node.setEdges(edges);

//                node.filterEdgeProperty();
                result.add(node);
            }

            return result;
        }

        return Lists.newArrayList();
    }

    /**
     * 生成邻居节点实体类
     *
     * @param nodeObject
     * @param
     * @return
     */
    private NeighbourNodeDTO buildNeighbourNodeDTO(JSONObject nodeObject) {
        NeighbourNodeDTO nodeData = new NeighbourNodeDTO();
        nodeData.setVid(nodeObject.getString("identity"));
        nodeData.setNodeType(nodeObject.getString("label"));
        JSONObject propertyObject = nodeObject.getJSONObject("properties");
        nodeData.setProperties(propertyObject);
        return nodeData;
    }

    private EdgeDataDTO buildEdgeDataDTO(String paceName, String subGraph, JSONObject edgeObject, JSONObject edgeProperties, Map<String, JSONObject> nodePropertiesMap) {
        EdgeDataDTO edgeData = new EdgeDataDTO();
        edgeData.setEdgeType(edgeObject.getString("label_name"));
        JSONObject propertyObject = edgeObject.getJSONObject("properties");
        edgeData.setProperties(propertyObject);
        String nameValue = null;
        edgeData.setRank(edgeObject.getLong("rank"));

        // 获取头尾节点数据实体
        String srcVid = edgeObject.getString("src");
        NodeDataDTO srcNode = getNodeDataDTOByVid(paceName, subGraph, srcVid, nodePropertiesMap);
        edgeData.setSrc(srcNode);
        String dstVid = edgeObject.getString("dst");
        NodeDataDTO dstNode = getNodeDataDTOByVid(paceName, subGraph, dstVid, nodePropertiesMap);
        edgeData.setDst(dstNode);
        edgeData.setName(nameValue);

        return edgeData;
    }

    private NodeDataDTO getNodeDataDTOByVid(String spaceName, String subGraph, String vidVal, Map<String, JSONObject> nodePropertiesMap) {
        String cypher = "match (v) where id(v) == \"" + vidVal + "\" return v;";
        String resultStr = graphTemplate.callCypher(subGraph, cypher);
        JSONArray jsonArray = JSON.parseArray(resultStr);
        if (jsonArray.size() > 0) {
            JSONObject jsonObject = jsonArray.getJSONObject(0);
            JSONObject nodeObject = jsonObject.getJSONObject("v");
            String nodeType = nodeObject.getString("label");
            JSONObject nodeProperties = nodePropertiesMap.get(nodeType);
            if (nodeProperties == null) {
//                nodeProperties = getNodeProperties(spaceName, nodeType);
                nodePropertiesMap.put(nodeType, nodeProperties);
            }
            NodeDataDTO nodeData = buildNodeDataDTO(nodeObject);
            return nodeData;
        }
        return null;
    }

    /**
     * 生成节点数据实体类
     *
     * @param nodeObject
     * @param
     * @return
     */
    private NodeDataDTO buildNodeDataDTO(JSONObject nodeObject) {
        NodeDataDTO nodeData = new NodeDataDTO();
        nodeData.setVid(nodeObject.getString("identity"));
        nodeData.setNodeType(nodeObject.getString("label"));
        JSONObject propertyObject = nodeObject.getJSONObject("properties");
        nodeData.setProperties(propertyObject);
        return nodeData;
    }

    /**
     * 收集共通邻居节点vid
     *
     * @param neighbourVids
     * @param neighbourResultStr
     * @param vid1
     * @param vid2
     */
    private void collectNeighbourVids(Set<String> neighbourVids, String neighbourResultStr, String vid1, String vid2) {
        JSONArray jsonArray = JSON.parseArray(neighbourResultStr);
        for (int i = 0; i < jsonArray.size(); i++) {
            JSONObject jsonObject = jsonArray.getJSONObject(i);
            String vid = jsonObject.getString("$-.neighbor");
            if (!vid.equals(vid1) && !vid.equals(vid2)) {
                neighbourVids.add(vid);
            }
        }
    }

    /**
     * 拼装边类型过滤条件
     *
     * @param edgeTypes
     * @return
     */
    private String neighbourSearchOfEdgeTypes(List<String> edgeTypes) {
        if (CollectionUtils.isEmpty(edgeTypes)) {
            return "*";
        }
        return StringUtils.join(edgeTypes, ",");
    }

    /**
     * 拼装节点过滤条件
     *
     * @param nodeSearchRequests
     * @return
     */
    private String neighbourSearchOfNodeFilter(List<NodeSearchRequest> nodeSearchRequests, String neighbour) {
        if (CollectionUtils.isEmpty(nodeSearchRequests)) {
            return "";
        }
        StringBuilder sb = new StringBuilder("WHERE ");
        for (int i = 0; i < nodeSearchRequests.size(); i++) {
            NodeSearchRequest nodeSearchRequest = nodeSearchRequests.get(i);
            if (i > 0) {
                sb.append(" or ");
            }
            sb.append("(");
            sb.append(" left(").append(neighbour).append(", ").append(getNodeTypeByteLegnth(nodeSearchRequest.getNodeType())).append(") == \"").append(nodeSearchRequest.getNodeType()).append("\"");
            if (CollectionUtils.isNotEmpty(nodeSearchRequest.getSearchConditions())) {
                sb.append(" and (");
                for (int j = 0; j < nodeSearchRequest.getSearchConditions().size(); j++) {
                    SearchConditionRequest searchCondition = nodeSearchRequest.getSearchConditions().get(j);
                    if (j > 0) {
                        sb.append(" ").append(searchCondition.getLogicalOperator()).append(" ");
                    }
                    String operator = "=".equals(searchCondition.getOperator()) ? "==" : searchCondition.getOperator();
                    if ("like".equalsIgnoreCase(operator)) {
                        operator = "CONTAINS";
                    }
//                    sb.append("properties($$).").append(searchCondition.getPropertyName()).append(" ").append(operator)
//                            .append(" ").append(ofNebulaPropertyValue(searchCondition.getPropertyType(), searchCondition.getValue()));
                }
                sb.append(")");
            }
            sb.append(")");

        }
        return sb.toString();
    }

    /**
     * 获取节点类型字节数长度，其中中文字符长度*3
     *
     * @param nodeType
     * @return
     */
    private int getNodeTypeByteLegnth(String nodeType) {
        int result = 0;
        char[] charArray = nodeType.toCharArray();
        for (int i = 0; i < charArray.length; i++) {
            if ((charArray[i] >= 0x4e00) && (charArray[i] <= 0x9fbb)) {
                result += 3;
            } else {
                result += 1;
            }

        }
        return result;

    }

    /**
     * 获取Nebula属性值
     *
     * @param propertyType
     * @param propertyValue
     * @return
     */
    private String ofNebulaPropertyValue(String propertyType, String propertyValue) {
        if (StringUtils.indexOf(propertyType, "STRING") >= 0
                || StringUtils.indexOf(propertyType, "VARCHAR") >= 0
                || StringUtils.indexOf(propertyType, "CHAR") >= 0) {
            return "'" + propertyValue + "'";
        } else if (StringUtils.indexOf(propertyType, "DATE") >= 0) {
            return "date(\"" + propertyValue + "\")";
        } else if (StringUtils.indexOf(propertyType, "DATETIME") >= 0) {
            return "datetime(\"" + propertyValue + "\")";
        } else {
            return propertyValue;
        }
    }

    private GraphDataDTO buildGraphData(String resultJSON, String spaceName) throws Exception {
        GraphDataDTO graphDataDTO = new GraphDataDTO();

        Map<String, NodeDataDTO> distinctNodes = Maps.newHashMap();
        List<EdgeDataDTO> edges = Lists.newArrayList();
        List<NebulaEdgeResult> edgesJSON = JSONArray.parseArray(resultJSON, NebulaEdgeResult.class);
        if (CollectionUtils.isNotEmpty(edgesJSON)) {
            for (NebulaEdgeResult edge : edgesJSON) {
                NebulaEdge e = edge.getE();
                String src = e.getSrc();
                String dst = e.getDst();
                //label-->nodeData
                String srcJSON = graphTemplate.callCypher(spaceName,
                        String.format("match (v) where id(v) == '%s' return v;", src.toUpperCase(Locale.ROOT)));
                String dstJSON = graphTemplate.callCypher(spaceName,
                        String.format("match (v) where id(v) == '%s' return v;", dst.toUpperCase(Locale.ROOT)));
                log.info("srcJSON:{}", srcJSON);
                log.info("dstJSON:{}", dstJSON);
                Optional<NebulaNodeResult> srcNodeOptional = JSONArray.parseArray(srcJSON, NebulaNodeResult.class).stream().findFirst();
                Optional<NebulaNodeResult> dstNodeOptional = JSONArray.parseArray(dstJSON, NebulaNodeResult.class).stream().findFirst();
                //NebulaNode ---> NodeDataDTO
                NodeDataDTO srcNodeDTO = null;
                if (srcNodeOptional.isPresent()) {
                    srcNodeDTO = convertNebulaNode2NodeDTO(srcNodeOptional.get().getV());
                    distinctNodes.put(srcNodeDTO.getVid(), srcNodeDTO);
                }
                NodeDataDTO dstNodeDTO = null;
                if (dstNodeOptional.isPresent()) {
                    dstNodeDTO = convertNebulaNode2NodeDTO(dstNodeOptional.get().getV());
                    distinctNodes.put(dstNodeDTO.getVid(), dstNodeDTO);
                }

                //NebulaEdge --> EdgeDataDTO
                LinkedHashMap<String, Object> properties = e.getProperties();
                Object edgeType = properties.get("name");
                EdgeDataDTO edgeDTO = new EdgeDataDTO();
                edgeDTO.setSrc(srcNodeDTO);
                edgeDTO.setDst(dstNodeDTO);
                edgeDTO.setEdgeType(!Objects.isNull(edgeType) ? edgeType.toString() : null);
                edgeDTO.setRank(e.getRank());
                edgeDTO.setProperties(JSONObject.parseObject(JSONObject.toJSONString(e.getProperties())));
                edges.add(edgeDTO);
            }
        }
        List<NodeDataDTO> nodes = new ArrayList<>(distinctNodes.values());
        graphDataDTO.setNodeList(nodes);
        graphDataDTO.setEdgeList(edges);
        //移除悬挂边
//        List<EdgeDataDTO> edgeList = graphDataDTO.getEdgeList();
//        edgeList.removeIf(oneEdge -> Objects.isNull(oneEdge.getSrc()) || Objects.isNull(oneEdge.getDst()));
        return graphDataDTO;
    }

    private NodeDataDTO convertNebulaNode2NodeDTO(NebulaNode nebulaNode) {
        NodeDataDTO nodeDataDTO = BeanUtil.copyProperties(nebulaNode, NodeDataDTO.class);
        nodeDataDTO.setNodeType(nebulaNode.getLabel());
        nodeDataDTO.setVid(nebulaNode.getIdentity());
        nodeDataDTO.setProperties(JSONObject.parseObject(JSON.toJSONString(nebulaNode.getProperties())));
        return nodeDataDTO;
    }

    @Override
    public GraphDataDTO subGraph(String spaceName) throws ApplicationException {
        GraphDataDTO graphDataDTO;
        //查询所有的边
        List<String> edges = getEdges(spaceName);
        String vid;
        SubGraphCenter subGraphCenter = null;
        String subGraphCenterStr = redissonUtils.get(SUB_GRAPH_PREFIX + spaceName);
        if(StringUtils.isNotBlank(subGraphCenterStr))
            subGraphCenter = JSONObject.parseObject(subGraphCenterStr,SubGraphCenter.class);
        if (subGraphCenter != null) {
            vid = subGraphCenter.getVid();
            String cypher = String.format("match (v)-[r]-(v2) where id(v) == \"%s\" return v,r,v2", vid);
            if (subGraphCenter.getEdgeLimit() >= 10) {
                cypher += " limit 50";
            }
            String result = graphTemplate.callCypher(spaceName, cypher);
            GraphData subGraph = graphDataParser.parseJsonToGraphData(spaceName, result);
            graphDataDTO = BeanUtil.copyProperties(subGraph, GraphDataDTO.class);
//            fillEdgeIdAndStyle(schemaId, graphDataDTO);
            return graphDataDTO;
        } else {
            //1. 获取边数大于10的节点
            //1.1 将节点1都展开（边数限制50）
            for (String edge : edges){
                graphDataDTO = getSubGraph(spaceName, edge, 10, 50);
                if(Objects.isNull(graphDataDTO))
                    continue;
                return graphDataDTO;
            }

            //2.1 将节点1端展开（不限制边数）
            //2.1 将节点1端展开（不限制边数）
            for (String edge : edges){
                graphDataDTO = getSubGraph(spaceName, edge, 3, null);
                if(Objects.isNull(graphDataDTO))
                    continue;
                return graphDataDTO;
            }

            //3.如果没有节点，则随机查询出5条边
            int maxEdgeCount = 0;
            GraphDataDTO retGraphDataDTO = null;
            for (String edge : edges) {
                try {
                    String cypher = "match (n)-[r:`" + edge + "`]-(m) return n,r,m limit 5";
                    String result = graphTemplate.callCypher(spaceName, cypher);
                    GraphData subGraph = graphDataParser.parseJsonToGraphData(spaceName, result);
                    graphDataDTO = BeanUtil.copyProperties(subGraph, GraphDataDTO.class);
                    if (graphDataDTO.getEdgeList().size() > maxEdgeCount || maxEdgeCount == 0) {
                        maxEdgeCount = graphDataDTO.getEdgeList().size();
                        retGraphDataDTO = graphDataDTO;
                    }
                } catch (Exception ex) {
                    log.error("异常，及有可能是图中" + edge + "不存在。", ex);
                }
            }
            return retGraphDataDTO;
        }
    }

    private GraphDataDTO getSubGraph(String spaceName, String edge, Integer cnt, Integer edgeLimit) {
        String vid = null;
        GraphDataDTO graphDataDTO = null;
        SubGraphCenter subGraphCenter = null;
        try {

            String cypher = "MATCH (a)-[t:" + edge + "]-(b) \n" +
                    "WITH id(a) as id, count(t) as cnt\n" +
                    "where cnt > " + cnt + "\n" +
                    "return id, cnt limit 1";
            String result = graphTemplate.callCypher(spaceName, cypher);
            if (!StringUtils.isEmpty(result) && !"null".equals(result) && !"[]".equals(result)) {
                JSONArray rows = JSONArray.parseArray(result);
                JSONObject row = rows.getJSONObject(0);
                vid = row.getString("id");
            }

            if (!StringUtils.isEmpty(vid)) {
                //保存入redis
                subGraphCenter = new SubGraphCenter();
                subGraphCenter.setSpaceName(spaceName);
                subGraphCenter.setVid(vid);
                subGraphCenter.setEdgeLimit(10);
                redissonUtils.set(SUB_GRAPH_PREFIX + spaceName, JSONObject.toJSONString(subGraphCenter),24L, TimeUnit.HOURS);
                cypher = String.format("match (v)-[r]-(v2) where id(v) == \"%s\" return v,r,v2 " + (Objects.isNull(edgeLimit) ? "" : " limit " + edgeLimit), vid);
                result = graphTemplate.callCypher(spaceName, cypher);
                GraphData subGraph = graphDataParser.parseJsonToGraphData(spaceName, result);
                graphDataDTO = BeanUtil.copyProperties(subGraph, GraphDataDTO.class);
//                    fillEdgeIdAndStyle(schemaId, graphDataDTO);
                return graphDataDTO;
            }
        } catch (Exception ex) {
            log.error("异常，及有可能是图中" + edge + "不存在。", ex);
        }
        return graphDataDTO;
    }

    private List<String> getEdges(String spaceName) {
        String cypher = "SHOW EDGES";
        String result = graphTemplate.callCypher(spaceName, cypher);
        if (StringUtils.isEmpty(result))
            throw new ApplicationException(ErrCodeEnum.NO_GRAPH_EDGE_ERROR);
        List<JSONObject> edges = JSONObject.parseArray(result, JSONObject.class);
        return edges.stream().map(e -> e.getString("Name")).collect(Collectors.toList());
    }
}
