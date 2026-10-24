package com.gientech.ragcommon.graph.dto;

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONArray;
import com.alibaba.fastjson.JSONException;
import com.alibaba.fastjson.JSONObject;
import com.alibaba.fastjson.parser.Feature;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.collections4.CollectionUtils;
import org.apache.commons.compress.utils.Lists;
import org.apache.commons.lang3.StringUtils;

import java.util.*;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

/**
 * 图数据DTO类
 */
@Data
@Builder
@AllArgsConstructor
@NoArgsConstructor
@Slf4j
public class GraphDataDTO {
    /**
     * 节点列表
     */
    private List<NodeDataDTO> nodeList;

    /**
     * 边列表
     */
    private List<EdgeDataDTO> edgeList;

    // 查询结果表格数据
    private List<CypherResultTableRow> tableRows;


    /**
     * 过滤边属性（weight属性）
     */
//    public void filterEdgeProperty() {
//        if (CollectionUtils.isNotEmpty(edgeList)) {
//            for (EdgeDataDTO oneEdge : edgeList) {
//                oneEdge.removeWeightProperty();
//            }
//        }
//    }


    @Data
    public static class CypherResultTableRow {
        private int id;//每一行定义一个ID方便前端渲染。
        private List<CypherResultItem> props;
    }

    @Data
    public static class CypherResultItem {
        // 列类型。EDGE：边；NODE：节点；OTHER：其他
        private String type;
        private String name;
        //列内容
        private String columnContent;
        private String content;
        private String id;
    }

    public void parseRawResult2TableRow(String result) {
        if (StringUtils.isBlank(result)) {
            return;
        }
        ObjectMapper objectMapper = new ObjectMapper();

//        this.generateEdgeId();
        List<CypherResultTableRow> rows = Lists.newArrayList();
        JSONArray rowsJsonArray = (JSONArray)JSON.parse(result, Feature.OrderedField);
        //遍历每一行
        for (int i = 0; i < rowsJsonArray.size(); i++) {
            CypherResultTableRow oneRow = new CypherResultTableRow();
            oneRow.setId(i+1);
            List<CypherResultItem> props = new ArrayList<>();
            oneRow.setProps(props);

            JSONObject rowObject = rowsJsonArray.getJSONObject(i);
            Set<String> columnKeys = rowObject.keySet();
            //遍历每一列
            for (String columnKey : columnKeys) {
                JSONObject rowColumnObject = null;
                Set<String> elementKeys = new HashSet<>();
                try {
                    rowColumnObject = JSONObject.parseObject(rowObject.getString(columnKey));
                    if(rowColumnObject!=null) {
                        elementKeys = rowColumnObject.keySet();
                    }
                }catch(JSONException ex){
                    //如果无法解析，就是Other类型
                }
                if (elementKeys != null && elementKeys.contains("src") && elementKeys.contains("dst")) {
                    //列是边数据
                    CypherResultItem column = new CypherResultItem();
                    column.setType("EDGE");
                    column.setName(columnKey);
                    String srcId = rowColumnObject.getString("src");
                    String dstId = rowColumnObject.getString("dst");
                    String labelName = rowColumnObject.getString("label_name");
                    //Long rank = rowColumnObject.getLong("rank");
                    EdgeDataDTO edge = null;
                    for(EdgeDataDTO e:edgeList){
                        if(( e.getSrc()==null && srcId==null ||srcId !=null &&  e.getSrc()!=null && srcId.equals(e.getSrc().getVid()))
                                && (e.getDst() ==null && dstId == null || dstId!=null && e.getDst()!=null && e.getDst()!=null && dstId.equals(e.getDst().getVid()))
                                && e.getEdgeType() !=null && e.getEdgeType().equals(labelName)){
                            edge = e;
                            break;
                        }
                    }
                    try {
                        column.setContent(objectMapper.writeValueAsString(edge));
                    } catch (JsonProcessingException e) {
                        log.error(e.getMessage(), e);
                        throw new RuntimeException(e);
                    }
                    if(Objects.isNull(edge)){
                        continue;
                    }
                    column.setId(edge.getId());
                    StringBuilder columnContentStrBuilder = new StringBuilder();
                    columnContentStrBuilder.append("[:")
                            .append(rowColumnObject.getString("label_name")).append(" ")
                            .append("\"").append(rowColumnObject.getString("src")).append("\"").append("->")
                            .append("\"").append(rowColumnObject.getString("dst")).append("\"").append(" ");

                    JSONObject propertyObject = rowColumnObject.getJSONObject("properties");
                    if (Objects.nonNull(propertyObject)) {
                        columnContentStrBuilder.append("{");
                        Set<String> propertyKeys = propertyObject.keySet();
                        for (String propertyKey : propertyKeys) {
                            String value = propertyObject.getString(propertyKey);
                            columnContentStrBuilder.append(propertyKey)
                                    .append(":")
                                    .append("\"")
                                    .append(value)
                                    .append("\"")
                                    .append(";");
                        }
                        columnContentStrBuilder.append("}");
                    }

                    columnContentStrBuilder.append("]");
                    String columnContentStr = columnContentStrBuilder.toString().replaceAll(";}", "}");
                    column.setColumnContent(columnContentStr);
                    props.add(column);
                } else if (elementKeys != null && elementKeys.contains("identity")) {
                    //列是节点数据
                    String vid = rowColumnObject.getString("identity");
                    String label = rowColumnObject.getString("label");
                    CypherResultItem column = new CypherResultItem();
                    column.setType("NODE");
                    column.setName(columnKey);
                    NodeDataDTO node = null;
                    for(NodeDataDTO n:nodeList){
                        if(n.getNodeType() != null && n.getNodeType().equals(label)
                                && n.getVid() != null && n.getVid().equals(vid)){
                            node = n;
                            break;
                        }
                    }
                    try {
                        node.setProperties(rowColumnObject.getJSONObject("properties"));
                        column.setContent(objectMapper.writeValueAsString(node));
                    } catch (JsonProcessingException e) {
                        log.error(e.getMessage(), e);
                        throw new RuntimeException(e);
                    }
                    column.setId(vid);
                    StringBuilder columnContentStrBuilder = new StringBuilder();
                    columnContentStrBuilder.append("(");
                    columnContentStrBuilder.append("\"")
                            .append(rowColumnObject.getString("identity"))
                            .append("\":")
                            .append(rowColumnObject.getString("label"));
                    JSONObject propertyObject = rowColumnObject.getJSONObject("properties");
                    if (Objects.nonNull(propertyObject)) {
                        columnContentStrBuilder.append("{");
                        Set<String> propertyKeys = propertyObject.keySet();
                        for (String propertyKey : propertyKeys) {
                            String value = propertyObject.getString(propertyKey);
                            columnContentStrBuilder.append(propertyKey)
                                    .append(":")
                                    .append("\"")
                                    .append(value)
                                    .append("\"")
                                    .append(";");
                        }
                        columnContentStrBuilder.append("}");
                    }

                    columnContentStrBuilder.append(")");
                    String columnContentStr = columnContentStrBuilder.toString().replaceAll(";}", "}");
                    column.setColumnContent(columnContentStr);
                    props.add(column);
                } else {
                    //列是属性或者统计信息
                    CypherResultItem column = new CypherResultItem();
                    //
                    if(rowObject.get(columnKey) instanceof String){
                        //是字符型
                        column.setType("OTHER");
                    } else {
                        //其他
                        String value = rowObject.getString(columnKey);
                        if(value!=null) {
                            Pattern pattern = Pattern.compile("^[-]?[\\d]+[.]?[\\d]*$");
                            Pattern scientificPattern = Pattern.compile("^[-]?(\\d+\\.?\\d*|\\.\\d+)[Ee][-+]?\\d+$");
                            if (pattern.matcher(value).matches() || scientificPattern.matcher(value).matches()) {
                                column.setType("NUMBER");
                            } else {
                                column.setType("OTHER");
                            }
                        }else{
                            column.setType("OTHER");
                        }
                    }
                    column.setName(columnKey);
                    column.setContent(rowObject.getString(columnKey));
                    column.setColumnContent(rowObject.getString(columnKey));
                    column.setId((i+1)+columnKey);
                    props.add(column);
                }
            }/* for columnKeys */

            rows.add(oneRow);
        }

        this.tableRows = rows;
    }

//    public void generateEdgeId() {
//        if (CollectionUtils.isEmpty(edgeList)) {
//            return;
//        }
//        for(EdgeDataDTO oneEdge:edgeList){
//            String id = generateEdgeId(oneEdge);
//            oneEdge.setId(id);
//        }
//    }

//    public static String generateEdgeId(EdgeDataDTO edgeDataDTO){
//        if (Objects.isNull(edgeDataDTO.getSrc()) || Objects.isNull(edgeDataDTO.getDst()))
//            return edgeDataDTO.getEdgeType();
//        else
//            return edgeDataDTO.getSrc().getVid() + "-" + edgeDataDTO.getEdgeType() + "-" + edgeDataDTO.getDst().getVid() + "-" + edgeDataDTO.getRank();
//    }
}
