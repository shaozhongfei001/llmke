package com.gientech.raggraphservice.domain.service.impl;

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONArray;
import com.alibaba.fastjson.JSONObject;
import com.alibaba.fastjson.serializer.SerializerFeature;
import com.gientech.raggraphservice.domain.service.GraphTemplate;
import com.gientech.raggraphservice.infrastructure.NebulaGraphConfig;
import com.google.common.collect.Maps;
import com.vesoft.nebula.client.graph.SessionPool;
import com.vesoft.nebula.client.graph.data.*;
import com.vesoft.nebula.client.graph.exception.*;
import jakarta.annotation.Resource;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.cloud.context.config.annotation.RefreshScope;
import org.springframework.stereotype.Component;
import java.io.UnsupportedEncodingException;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

@RefreshScope
@Component
@Slf4j
@ConditionalOnProperty(name = "graph.type", havingValue = "nebula")
public class NebulaGraphTemplate implements GraphTemplate {

    @Resource
    private NebulaGraphConfig nebulaGraphConfig;

//    @Value("${spring.profiles.active}")
//    private String profile = "prod";
//
//    @Value("${nebula.support-multi-env:false}")
//    private Boolean supportMultiEnv;

    @Value("${nebula.partitionNum}")
    private String partitionNum;

    @Value("${nebula.replicaFactor}")
    private String replicaFactor;

    private ConcurrentHashMap<String, SessionPool> sessionPoolMap = new ConcurrentHashMap<>();

    private SessionPool getSessionPool(String spaceName) {
        if (sessionPoolMap.get(spaceName) == null) {
            SessionPool sessionPool = nebulaGraphConfig.getSessionPool(spaceName);
            sessionPoolMap.put(spaceName, sessionPool);
            return sessionPool;
        }
        return sessionPoolMap.get(spaceName);
    }

    /**
     * 废除掉一个SessionPool（为了解决Session过期的问题）
     *
     * @param spaceName
     * @return
     */
    private SessionPool disuseSessionPool(String spaceName) {
        SessionPool sessionPool = sessionPoolMap.get(spaceName);
        if (sessionPool == null) {
            //sessionPool 本身就不存在
            return null;
        }
        sessionPoolMap.remove(spaceName);
        sessionPool.close();
        return sessionPool;
    }

    /**
     * 子图名，变成空间名(加环境前缀)。
     * @param subGraph
     * @return
     */
    private String getSpaceName(String subGraph) {
        return subGraph;
    }

    /**
     * 执行cypher语句
     *
     * @param subGraph
     * @param cypher
     * @return
     * @throws IOErrorException
     * @throws ClientServerIncompatibleException
     * @throws BindSpaceFailedException
     * @throws AuthFailedException
     */
    private ResultSet execute(String subGraph, String cypher) throws IOErrorException, ClientServerIncompatibleException,
            BindSpaceFailedException, AuthFailedException {
        String spaceName = "test";
        if (!StringUtils.isEmpty(subGraph)) {
            spaceName = getSpaceName(subGraph);
        }
        try {
            ResultSet resultSet = getSessionPool(spaceName).execute(cypher);
            if (resultSet.getErrorCode() == -1002 && resultSet.getErrorMessage().contains("Session not existed")) {
                //session失效,重新获取session并执行
                SessionPool sessionPool = nebulaGraphConfig.getSessionPool(spaceName);
                sessionPoolMap.put(spaceName, sessionPool);
                return sessionPool.execute(cypher);
            }
            return resultSet;
        } catch (IOErrorException | ClientServerIncompatibleException | AuthFailedException | BindSpaceFailedException e) {
//            SessionPool sessionPool = nebulaGraphConfig.getSessionPool(spaceName);
//            sessionPoolMap.put(spaceName, sessionPool);
//            return sessionPool.execute(cypher);
            throw e;
        }
    }

    private ResultSet execute(String cypher) throws IOErrorException, ClientServerIncompatibleException,
            BindSpaceFailedException, AuthFailedException {
        return execute(null, cypher);
    }

    /**
     * 判断节点/边类型是否存在
     *
     * @param label
     * @param isVertex true-vertex false-edge
     * @return
     */
    @Override
    public boolean isExistType(String subGraph, String label, boolean isVertex) {
        try {
            StringBuilder stmt = new StringBuilder();
            if (isVertex) {
                stmt.append(" DESC TAG ").append(label).append(";");
            } else {
                stmt.append(" DESC EDGE ").append(label).append(";");
            }
            ResultSet result = execute(subGraph, stmt.toString());
            if (!result.isSucceeded() && -1005 != result.getErrorCode()) {//其他原因造成失败，（-1005 是因为 space 不存在造成的失败）
                throw new RuntimeException("Desc space fail:" + result.getErrorCode() + ":" + result.getErrorMessage());
            }
            return result.isSucceeded();
        } catch (IOErrorException | ClientServerIncompatibleException |
                 AuthFailedException | BindSpaceFailedException e) {
            throw new RuntimeException(e);
        }
    }

    /**
     * 针对顶点，格式封装成这样：
     * <p>
     * {
     * "schema":{
     * "label":"学生",
     * "primary":"id",
     * "properties":[
     * {
     * "index":false,
     * "name":"...",
     * "optional":true,
     * "type":"STRING"
     * },
     * ...
     * ],
     * "type":"VERTEX"
     * }
     * }
     * </p>
     * 针对边：
     * {
     * "schema":{
     * "constraints":[["学生","老师"]],
     * "label":"选课",
     * "properties":[
     * {
     * "index":false,
     * "name":"课程名",
     * "optional":true,
     * "type":"STRING"
     * }
     * ],
     * "type":"EDGE"
     * }
     * }
     *
     * @param subGraph
     * @param label
     * @param isVertex true-vertex false-edge
     * @return
     */
    @Override
    public String getLabelSchema(String subGraph, String label, boolean isVertex) {
        try {
            StringBuilder stmt = new StringBuilder();
            if (isVertex) {
                stmt.append("DESC TAG ").append(label).append(";");
            } else {
                stmt.append("DESC EDGE ").append(label).append(";");
            }
            ResultSet resultSet = execute(subGraph, stmt.toString());
            if (!resultSet.isSucceeded()) {
                throw new RuntimeException("The statement execute fail:" + resultSet.getErrorCode() + ":" + resultSet.getErrorMessage());
            }
            System.out.println("cols:" + resultSet.getColumnNames());
            StringBuilder sb = new StringBuilder("{");
            sb.append("\"schema\":{");
            sb.append("\"label\":\"").append(label).append("\",");
            sb.append("\"properties\":[");
            for (int i = 0; i < resultSet.rowsSize(); i++) {
                ResultSet.Record record = resultSet.rowValues(i);
                if (i > 0) {
                    sb.append(",");
                }
                sb.append("{");
                sb.append("\"index\":false,");
                sb.append("\"name\":").append(toJson(record.get("Field"))).append(",");
                String isNull = toJson(record.get("Null"));
                sb.append("\"optional\":").append("yes".equalsIgnoreCase(isNull) ? "true" : "false").append(",");
                sb.append("\"type\":").append(toJson(record.get("Type")));
                sb.append("}");
            }
            sb.append("],");
            if (isVertex) {
                sb.append("\"type\":\"VERTEX\"");
            } else {
                sb.append("\"type\":\"EDGE\"");
            }
            sb.append("}");
            sb.append("}");
            return sb.toString();
        } catch (IOErrorException | UnsupportedEncodingException | ClientServerIncompatibleException |
                 AuthFailedException | BindSpaceFailedException e) {
            throw new RuntimeException(e);
        }
    }

    /**
     * 相关json组装可查看 OntologyAppServiceImpl.buildTuGraphSchema 函数
     * [{
     * label:'学生',
     * type":"VERTEX",
     * primary:"name",
     * properties:[{
     * name:'name',
     * type:'STRING',
     * optional:false,
     * unique:true,
     * index:true
     * },
     * ...
     * ]
     * },
     * {
     * label:'选课',
     * type":"EDGE",
     * properties:[
     * ...
     * ]
     * }]
     *
     * @param subGraph
     * @param schema
     * @return
     * @throws UnsupportedEncodingException
     */
//    @Override
//    public boolean importSchemaFromContent(String subGraph, String schema) throws UnsupportedEncodingException {
//        List<String> successedVertexLabels = new ArrayList<>();
//        List<String> successedEdgeLabels = new ArrayList<>();
//        try {
//            JSONObject obj = JSONObject.parseObject(schema);
//            JSONArray objArray = obj.getJSONArray("schema");
//
//            for (int i = 0; i < objArray.size(); i++) {
//                JSONObject graphObj = objArray.getJSONObject(i);
//                String type = graphObj.getString("type");
//                String label = graphObj.getString("label");
//                JSONArray properties = graphObj.getJSONArray("properties");
//                if ("VERTEX".equals(type)) {
//                    StringBuilder stmt = new StringBuilder("CREATE TAG ").append(label).append(" (");
//                    for (int j = 0; j < properties.size(); j++) {
//                        if (j > 0) {
//                            stmt.append(",");
//                        }
//                        JSONObject property = properties.getJSONObject(j);
//                        String name = property.getString("name");
//                        String dataType = property.getString("type");
//                        boolean optional = property.getBoolean("optional");
//                        stmt.append(name).append(" ").append(dataType);
//                        if (!optional) {
//                            stmt.append(" NOT NULL ");
//                        }
//                    }
//                    stmt.append(")");
//                    ResultSet resultSet = sessionPool.execute("USE " + subGraph + ";" + stmt.toString() + ";");
//
//                    if (!resultSet.isSucceeded()) {
//                        throw new RuntimeException("The statement execute fail:" + resultSet.getErrorCode() + ":" + resultSet.getErrorMessage());
//                    }
//                    successedVertexLabels.add(label);
//                } else if ("EDGE".equals(type)) {
//
//                    StringBuilder stmt = new StringBuilder("CREATE EDGE ").append(label).append(" (");
//                    for (int j = 0; j < properties.size(); j++) {
//                        if (j > 0) {
//                            stmt.append(",");
//                        }
//                        JSONObject property = properties.getJSONObject(j);
//                        String name = property.getString("name");
//                        String dataType = property.getString("type");
//                        boolean optional = property.getBoolean("optional");
//                        stmt.append(name).append(" ").append(dataType);
//                        if (!optional) {
//                            stmt.append(" NOT NULL ");
//                        }
//                    }
//                    stmt.append(")");
//                    ResultSet resultSet = sessionPool.execute("USE " + subGraph + ";" + stmt.toString() + ";");
//
//                    if (!resultSet.isSucceeded()) {
//                        throw new RuntimeException("The statement execute fail:" + resultSet.getErrorCode() + ":" + resultSet.getErrorMessage());
//                    }
//                    successedEdgeLabels.add(label);
//                }
//            }
//            return true;
//        } catch (Exception e) {
//            //如果发生异常先删除掉已经创建成功的
//            for (String label : successedVertexLabels) {
//                try {
//                    StringBuilder stmt = new StringBuilder("DROP TAG IF EXISTS ").append(label);
//                    sessionPool.execute(stmt.toString());
//                } catch (Exception ex) {
//                    log.error(ex.getMessage(), ex);
//                }
//            }
//            for (String label : successedEdgeLabels) {
//                try {
//                    StringBuilder stmt = new StringBuilder("DROP EDGE IF EXISTS ").append(label);
//                    sessionPool.execute(stmt.toString());
//                } catch (Exception ex) {
//                    log.error(ex.getMessage(), ex);
//                }
//            }
//            throw new RuntimeException(e);
//        }
//    }
    @Override
    public boolean importSchemaFromContent(String subGraph, String schema) {
        //把语句分开执行，有利于定位错误
        String[] cyphers = schema.split(";");
        String results = "";
        for (String cypher : cyphers) {
            if (StringUtils.isNotBlank(cypher)) {
                String res = callCypher(subGraph, cypher);
                results += res;
            }
        }
        log.info("importSchemaFromContent.res:{}", results);
        if (StringUtils.isNotBlank(results)) {
            return true;
        }
        return false;
    }

    /**
     * 执行语句nGQL语句,结果封装成json
     *
     * @param subGraph
     * @param cypher
     * @return
     */
    @Override
    public String callCypher(String subGraph, String cypher) {
        try {
            if (!cypher.endsWith(";")) {
                cypher += ";";
            }

            log.debug("graph {} exec cypher: {}", subGraph, cypher);

            ResultSet resultSet = execute(subGraph, cypher);
            if (resultSet.getErrorCode() == -1005 && resultSet.getErrorMessage().contains("SpaceNotFound")) {
                //如果SpaceName被删除的话则,删掉session重新再执行一下。
                disuseSessionPool(getSpaceName(subGraph));
                resultSet = execute(subGraph, cypher);
            }

            if (!resultSet.isSucceeded()) {
                log.error("graph {} exec cypher error: {}", subGraph, cypher);
                throw new RuntimeException("cypher exec failed:" + resultSet.getErrorCode() + ":"
                        + resultSet.getErrorMessage() + " -- graph:" + subGraph + ", cypher:" + cypher);
            }

            log.debug("resultSet.rowsSize():" + resultSet.rowsSize());

            //把返回结果封装成json
            JSONArray jsonArray = new JSONArray();
            //StringBuilder sb = new StringBuilder("[");
            if (resultSet.rowsSize() == 0) {
                return "[]";
            }
            for (int index = 0; index < resultSet.rowsSize(); index++) {
                ResultSet.Record record = resultSet.rowValues(index);
                JSONObject rowJson = new JSONObject(new LinkedHashMap());
                for (int i = 0; i < record.values().size(); i++) {
                    String colName = resultSet.getColumnNames().get(i);
                    ValueWrapper value = record.values().get(i);
                    rowJson.put(colName, toJsonValue(value));
                }
                jsonArray.add(rowJson);
            }
            return JSON.toJSONString(jsonArray, SerializerFeature.WriteMapNullValue);
        } catch (IOErrorException | UnsupportedEncodingException | ClientServerIncompatibleException |
                 AuthFailedException e) {
            log.error(e.getMessage(), e);
            throw new RuntimeException(e);
        } catch (Exception e) {
            e.printStackTrace();
            throw new RuntimeException(e);
        }
    }

    /**
     * 把 value 转成json可接受的值
     *
     * @param value
     * @return
     * @throws UnsupportedEncodingException
     */
    private Object toJsonValue(ValueWrapper value) throws UnsupportedEncodingException {
        if (value == null) {
            return null;
        } else if (value.isNull()) {
            return null;
        } else if (value.isLong()) {
            return value.asLong();
        } else if (value.isBoolean()) {
            return value.asBoolean();
        } else if (value.isDouble()) {
            return value.asDouble();
        } else if (value.isString()) {
            return value.asString();
        } else if (value.isTime()) {
            return value.asTime().getLocalTimeStr();
        } else if (value.isDate()) {
            return value.asDate().toString();
        } else if (value.isDateTime()) {
            return value.asDateTime().getLocalDateTimeStr();
        } else if (value.isVertex()) {
            Node node = value.asNode();
            return toJsonValue(node);
        } else if (value.isEdge()) {
            Relationship edge = value.asRelationship();
            return toJsonValue(edge);
        } else if (value.isEmpty()) {
            return "_EMPTY_";
        } else if (value.isNull()) {
            return "_NULL_";
        } else if (value.isPath()) {
            PathWrapper pathWrapper = value.asPath();
            return toJsonValue(pathWrapper);
            //throw new RuntimeException("Unsupport path type temporarily.");
        } else if (value.isList()) {
            ArrayList<ValueWrapper> list = value.asList();
            JSONArray arrayJson = new JSONArray();
            for (int i = 0; i < list.size(); i++) {
                arrayJson.add(toJsonValue(list.get(0)));
            }
            return arrayJson;
        } else if (value.isSet()) {
            throw new RuntimeException("Unsupport set type temporarily.");
        } else if (value.isMap()) {
            throw new RuntimeException("Unsupport map type temporarily.");
        } else {
            throw new RuntimeException("Unsupport data type.");
        }
    }

    private JSONObject toJsonValue(Node node) throws UnsupportedEncodingException {
        if (node == null) {
            return null;
        }
        JSONObject nodeJson = new JSONObject();
        ValueWrapper id = node.getId();
        String tagName = node.tagNames().get(0);
        nodeJson.put("identity", toJsonValue(id));
        nodeJson.put("label", tagName);
        JSONObject propsJson = new JSONObject();
        propsJson.put("id", toJsonValue(id));
        for (Map.Entry<String, ValueWrapper> entry : node.properties(node.tagNames().get(0)).entrySet()) {
            String propertyName = entry.getKey();
            ValueWrapper value = entry.getValue();
            propsJson.put(propertyName, toJsonValue(value));
        }
        nodeJson.put("properties", propsJson);
        return nodeJson;
    }


    private JSONObject toJsonValue(Relationship edge) throws UnsupportedEncodingException {
        if (edge == null) {
            return null;
        }
        JSONObject edgeJson = new JSONObject();
        ValueWrapper dstId = edge.dstId();
        ValueWrapper srcId = edge.srcId();
        String edgeName = edge.edgeName();
        edgeJson.put("src", toJsonValue(srcId));
        edgeJson.put("dst", toJsonValue(dstId));
        edgeJson.put("forward", true);
        edgeJson.put("identity", null);
        edgeJson.put("label_id", edgeName);
        edgeJson.put("label_name", edgeName);
        edgeJson.put("rank", edge.ranking());
        HashMap<String, ValueWrapper> properties = edge.properties();
        JSONObject propsJson = new JSONObject();
        for (Map.Entry<String, ValueWrapper> entry : properties.entrySet()) {
            String key = entry.getKey();
            ValueWrapper value = entry.getValue();
            propsJson.put(key, toJsonValue(value));
        }
        edgeJson.put("properties", propsJson);
        return edgeJson;
    }

    private JSONObject toJsonValue(PathWrapper path) throws UnsupportedEncodingException {
        JSONObject pathJson = new JSONObject();
        List<Relationship> relationships = path.getRelationships();
        JSONArray edgesJson = new JSONArray();
        /**
         * p:
         *      edges:  B->C, A->B
         *      nodes:
         *      step:
         *      briefPath: A->B->C
         *      startNode:
         */
        for (Relationship relationship : relationships) {
            JSONObject relationshipJson = new JSONObject();
            //获取值
            ValueWrapper srcId = relationship.srcId();
            ValueWrapper dstId = relationship.dstId();
            String edgeName = relationship.edgeName();
            long rank = relationship.ranking();

            //封装成EdgeDataDTO
            JSONObject srcNode = new JSONObject();
            srcNode.put("vid", toJsonValue(srcId));
            JSONObject dstNode = new JSONObject();
            dstNode.put("vid", toJsonValue(dstId));
            relationshipJson.put("src", srcNode);
            relationshipJson.put("dst", dstNode);
            relationshipJson.put("edgeType", edgeName);
            relationshipJson.put("rank", rank);

            edgesJson.add(relationshipJson);
        }
        pathJson.put("edges", edgesJson);
        JSONArray nodesJson = new JSONArray();
        List<Node> nodes = path.getNodes();
        for (Node node : nodes) {
            JSONObject nodeObject = new JSONObject();
            nodeObject.put("vid", toJsonValue(node.getId()));
            nodesJson.add(nodeObject);
        }
        pathJson.put("nodes", nodesJson);
        pathJson.put("step", relationships.size());
        pathJson.put("startNode", toJsonValue(path.getStartNode().getId()));
        pathJson.put("endNode", toJsonValue(path.getEndNode().getId()));
        String regEx = "\"|@(\\d)|\\{|\\}|:|\\s";
        Pattern pattern = Pattern.compile(regEx);
        Matcher matcher = pattern.matcher(path.toString());
        pathJson.put("briefPath", matcher.replaceAll(""));
        return pathJson;
    }

    /**
     * 把 value 转成json格式
     *
     * @param value
     * @return
     * @throws UnsupportedEncodingException
     */
    private String toJson(ValueWrapper value) throws UnsupportedEncodingException {
        StringBuilder sb = new StringBuilder("");
        if (value == null) {
            sb.append("null");
        } else if (value.isNull()) {
            sb.append("null");
        } else if (value.isLong()) {
            sb.append(value.asLong());
        } else if (value.isBoolean()) {
            sb.append(value.asBoolean());
        } else if (value.isDouble()) {
            sb.append(value.asDouble());
        } else if (value.isString()) {
            sb.append("\"").append(value.asString()).append("\"");
        } else if (value.isTime()) {
            sb.append("\"").append(value.asTime().getLocalTimeStr()).append("\"");
        } else if (value.isDate()) {
            sb.append("\"").append(value.asDate().toString()).append("\"");
        } else if (value.isDateTime()) {
            sb.append("\"").append(value.asDateTime().getLocalDateTimeStr()).append("\"");
        } else if (value.isVertex()) {
            Node node = value.asNode();
            sb.append(toJson(node));
        } else if (value.isEdge()) {
            Relationship edge = value.asRelationship();
            sb.append(toJson(edge));
        } else if (value.isEmpty()) {
            sb.append("\"_EMPTY_\"");
        } else if (value.isNull()) {
            sb.append("\"_NULL_\"");
        } else if (value.isPath()) {
            throw new RuntimeException("Unsupport path type temporarily.");
        } else if (value.isList()) {
            throw new RuntimeException("Unsupport list type temporarily.");
        } else if (value.isSet()) {
            throw new RuntimeException("Unsupport set type temporarily.");
        } else if (value.isMap()) {
            throw new RuntimeException("Unsupport map type temporarily.");
        } else {
            throw new RuntimeException("Unsupport data type.");
        }
        return sb.toString();
    }

    /**
     * 把节点实例 （node） 转成与 tuGraph一致的格式 ： {"identity":0,"label":"学生","properties":{"id":5,"name":"张三","姓名":null,"年龄":15,"性别":null,"电话":null}}
     *
     * @param node
     * @return
     * @throws UnsupportedEncodingException
     */
    private String toJson(Node node) throws UnsupportedEncodingException {
        if (node == null) {
            return null;
        }
        StringBuilder sb = new StringBuilder("{");
        ValueWrapper id = node.getId();
        String tagName = node.tagNames().get(0);
        sb.append("\"identity\":").append(toJson(id)).append(",");
        sb.append("\"label\":\"").append(tagName).append("\"").append(",");
        sb.append("\"properties\":{");
        sb.append("\"id\":").append(toJson(id));

        for (Map.Entry<String, ValueWrapper> entry : node.properties(node.tagNames().get(0)).entrySet()) {
            String propertyName = entry.getKey();
            ValueWrapper value = entry.getValue();
            sb.append(",\"").append(propertyName).append("\":").append(toJson(value));
        }
        sb.append("}");
        sb.append("}");
        return sb.toString();
    }

    /**
     * 把关系转变为 json
     * 格式如下：{"dst":1,"forward":true,"identity":0,"label_id":"选课","label_name":”选课“,"properties":{"课程名":"C++"},"src":0,"temporal_id":39154064}
     *
     * @param edge
     * @return
     * @throws UnsupportedEncodingException
     */
    private String toJson(Relationship edge) throws UnsupportedEncodingException {
        if (edge == null) {
            return null;
        }
        StringBuilder sb = new StringBuilder("{");
        ValueWrapper dstId = edge.dstId();
        ValueWrapper srcId = edge.srcId();
        String edgeName = edge.edgeName();
        sb.append("\"dst\":").append(toJson(dstId)).append(",");
        sb.append("\"forward\":true,");
        sb.append("\"identity\":null,");
        sb.append("\"label_id\":\"").append(edgeName).append("\"").append(",");
        sb.append("\"label_name\":\"").append(edgeName).append("\"").append(",");
        sb.append("\"rank\":").append(edge.ranking()).append(",");
        HashMap<String, ValueWrapper> properties = edge.properties();
        sb.append("\"properties\":{");
        int index = 0;
        for (Map.Entry<String, ValueWrapper> entry : properties.entrySet()) {
            if (index > 0) {
                sb.append(",");
            }
            String key = entry.getKey();
            ValueWrapper value = entry.getValue();
            sb.append("\"").append(key).append("\":").append(toJson(value));
            index++;
        }
        sb.append("},");
        sb.append("\"src\":").append(toJson(srcId));
        sb.append("}");
        return sb.toString();
    }

    /**
     * 实际上是 drop 语句
     *
     * @param subGraph
     * @param label
     * @param isVertex
     * @return
     */
    @Override
    public boolean deleteLabel(String subGraph, String label, boolean isVertex) {
        try {
            StringBuilder stmt = new StringBuilder();
            if (isVertex) {
                stmt.append(" DROP TAG ").append(label).append(";");
            } else {
                stmt.append(" DROP EDGE ").append(label).append(";");
            }
            ResultSet result = execute(subGraph, stmt.toString());
            if (!result.isSucceeded()) {
                log.error("create space fail:" + result.getErrorCode() + ":" + result.getErrorMessage());
            }
            return result.isSucceeded();
        } catch (IOErrorException | ClientServerIncompatibleException | AuthFailedException |
                 BindSpaceFailedException e) {
            throw new RuntimeException(e);
        }
    }

    @Override
    public boolean isExistVertex(String subGraph, String vid) {
        try {
            ResultSet result = execute(subGraph, String.format("match (v) where id(v) == '%s' return v", vid));
            if (!result.isSucceeded()) {//其他原因造成失败，（-1005 是因为 space 不存在造成的失败）
                return false;
            }
            return !result.isEmpty();

        } catch (IOErrorException | ClientServerIncompatibleException | AuthFailedException |
                 BindSpaceFailedException e) {
            throw new RuntimeException(e);
        }

    }

    @Override
    public String getNodesByType(String subGraph, String label) {
        String resultJSON = callCypher(subGraph, String.format("match (v:%s) return id(v) as identity", label));
        return resultJSON;
    }

    @Override
    public boolean createGraph(String subGraph, String description) {
        try {
            StringBuilder stmt = new StringBuilder("CREATE SPACE IF NOT EXISTS `").append(getSpaceName(subGraph)).append("`(partition_num=").append(partitionNum).append(",replica_factor=").append(replicaFactor).append(",vid_type=fixed_string(128))");
            if (StringUtils.isNotBlank(description)) {
                stmt.append(" COMMENT = '").append(description).append("'");
            }
            stmt.append(";");
            ResultSet result = execute(stmt.toString());
            if (!result.isSucceeded()) {
                log.error("create space fail:" + result.getErrorCode() + ":" + result.getErrorMessage());
            }
            return result.isSucceeded();
        } catch (IOErrorException | ClientServerIncompatibleException | AuthFailedException |
                 BindSpaceFailedException e) {
            throw new RuntimeException(e);
        }
    }

    /**
     * 判断spaceName是否存在（BebulaGraph 的 spaceName 相当于 TuGraph 中的 subGraph）
     *
     * @param subGraph
     * @return
     */
    @Override
    public boolean isExistGraph(String subGraph) {
        try {
            ResultSet result = execute("DESC space `" + getSpaceName(subGraph) + "`");
            if (!result.isSucceeded() && -1005 != result.getErrorCode()) {//其他原因造成失败，（-1005 是因为 space 不存在造成的失败）
                throw new RuntimeException("Desc space fail:" + result.getErrorCode() + ":" + result.getErrorMessage());
            }
            return result.isSucceeded();
        } catch (IOErrorException | ClientServerIncompatibleException | AuthFailedException |
                 BindSpaceFailedException e) {
            throw new RuntimeException(e);
        }
    }

    @Override
    public boolean deleteGraph(String subGraph) {
        try {
            ResultSet result = execute(String.format("DROP SPACE IF EXISTS `%s`", getSpaceName(subGraph)));
            if (!result.isSucceeded() && -1005 != result.getErrorCode()) {//其他原因造成失败，（-1005 是因为 space 不存在造成的失败）
                throw new RuntimeException("Desc space fail:" + result.getErrorCode() + ":" + result.getErrorMessage());
            }
            disuseSessionPool(getSpaceName(subGraph));
            return result.isSucceeded();
        } catch (IOErrorException | ClientServerIncompatibleException | AuthFailedException |
                 BindSpaceFailedException e) {
            throw new RuntimeException(e);
        }
    }

    @Override
    public boolean deleteBatchGraph(List<String> subGraphs) {
        try {
            String dropCypher = subGraphs.stream().map(subGraph -> getSpaceName(subGraph)).map(i -> "DROP SPACE IF EXISTS `" + i + "`").collect(Collectors.joining(";"));
            ResultSet result = execute(dropCypher);
            if (!result.isSucceeded() && -1005 != result.getErrorCode()) {//其他原因造成失败，（-1005 是因为 space 不存在造成的失败）
                throw new RuntimeException("Desc space fail:" + result.getErrorCode() + ":" + result.getErrorMessage());
            }
            for (String subGraph : subGraphs) {
                disuseSessionPool(getSpaceName(subGraph));
            }
            return result.isSucceeded();
        } catch (IOErrorException | ClientServerIncompatibleException | AuthFailedException |
                 BindSpaceFailedException e) {
            throw new RuntimeException(e);
        }
    }

    @Override
    public String getInstanceAmount(String subGraph) {

        Map<String, Long> resultMap = Maps.newHashMap();
        String resultJSON = "[]";

        String jobInfo = callCypher(subGraph, "SUBMIT JOB STATS;");
        log.info("execute submit job stats:{}", jobInfo);

        //查询job状态是否完成
        JSONObject statusObject = new JSONObject();
        statusObject.put("Status", "BEGIN");
        //设置条件避免死循环
        int count = 300;

        try {
            while (count > 0 && !statusObject.get("Status").toString().equals("FINISHED")) {
                String statusJSON = callCypher(subGraph, "show job " + jobInfo.replaceAll("[^0-9]+", ""));
                statusObject = JSON.parseArray(statusJSON, JSONObject.class).get(0);
                count--;
                Thread.sleep(500);
            }
        } catch (Exception ex) {
            log.error(ex.getMessage());
        }
        if (count == 0 && !statusObject.get("Status").toString().equals("FINISHED")) {
            return null;
        }

        resultJSON = callCypher(subGraph, "SHOW STATS;");

        log.info("resultJSON:{}", resultJSON);

        return resultJSON;


    }

    /**
     * 根据cypher语句查询节点列表
     *
     * @param subGraph
     * @param cypher
     * @return
     */
    public List<Node> getNodeListByCypher(String subGraph, String cypher) {
        try {
            if (!cypher.endsWith(";")) {
                cypher += ";";
            }

            List<Node> result = new ArrayList<>();
            log.info("getNodeListByCypher: {}", cypher);
            ResultSet resultSet = execute(subGraph, cypher);
            if (!resultSet.isSucceeded()) {
                throw new RuntimeException("The statement execute fail:" + resultSet.getErrorCode() + ":" + resultSet.getErrorMessage());
            }
            for (int index = 0; index < resultSet.rowsSize(); index++) {
                ResultSet.Record record = resultSet.rowValues(index);
                ValueWrapper value = record.values().get(0);
                Node node = value.asNode();
                result.add(node);
            }

            return result;
        } catch (IOErrorException | ClientServerIncompatibleException | AuthFailedException
                 | BindSpaceFailedException | InvalidValueException | UnsupportedEncodingException e) {
            log.error(e.getMessage(), e);
            throw new RuntimeException(e);
        }
    }

    @Override
    public void cloneSpaceSchema(String destSubGraph, String srcSubGraph) {
        String cypher = "CREATE SPACE IF NOT EXISTS " + getSpaceName(destSubGraph) + " AS "
                + getSpaceName(srcSubGraph);
        callCypher(srcSubGraph, cypher);
    }

    @Override
    public String getVidType(String subGraph) {
        String resultStr = callCypher(subGraph, "desc space `" + getSpaceName(subGraph) + "`");
        JSONArray jsonArray = JSONArray.parseArray(resultStr);
        return jsonArray.getJSONObject(0).getString("Vid Type");
    }
}
