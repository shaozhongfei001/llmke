package com.gientech.raggraphservice.application.service.impl;

import cn.hutool.core.bean.BeanUtil;
import com.alibaba.fastjson.JSON;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.graph.convertor.GraphDataDTOConvertor;
import com.gientech.ragcommon.graph.convertor.NodeDataDTOConvertor;
import com.gientech.ragcommon.graph.dto.*;
import com.gientech.ragcommon.graph.entity.GraphData;
import com.gientech.ragcommon.graph.entity.GraphInstance;
import com.gientech.ragcommon.graph.entity.Keyword;
import com.gientech.ragcommon.graph.entity.NodeData;
import com.gientech.ragcommon.graph.enums.GraphEnums;
import com.gientech.ragcommon.graph.enums.GraphFieldEnums;
import com.gientech.ragcommon.graph.request.EdgeSearchRequest;
import com.gientech.ragcommon.graph.request.KeywordSearchRequest;
import com.gientech.ragcommon.graph.request.NodeBatchSearchRequest;
import com.gientech.ragcommon.graph.request.NodeSearchRequest;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.raggraphservice.application.service.GraphQueryAppService;
import com.gientech.raggraphservice.domain.service.GraphQueryDomainService;
import com.google.common.collect.Lists;
import com.google.common.collect.Maps;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

import static com.gientech.ragcommon.graph.enums.GraphEnums.EDGE_TYPE_NAME;

@Service
@Slf4j
public class GraphQueryAppServiceImpl implements GraphQueryAppService {

    @Autowired
    private GraphQueryDomainService graphQueryDomainService;

    @Override
    public GraphDataDTO queryNodesByCondition(NodeSearchRequest searchContent) throws ApplicationException {
        try {
            GraphData graphData = graphQueryDomainService.queryNodesByCondition(searchContent);
            GraphDataDTO graphDataDTO = GraphDataDTOConvertor.INSTANCE.graphData2GraphDataDTO(graphData);
            return graphDataDTO;
        } catch (Exception ex) {
            log.error(ex.getMessage(), ex);
            throw new ApplicationException(ErrCodeEnum.EXECUTE_GRAPH_QUERY_ERROR.getErrCode(), ex.getMessage(),ex);
        }
    }

    @Override
    public GraphDataDTO queryEdgesByCondition(EdgeSearchRequest edgeSearchRequest) throws ApplicationException {
        try {
            GraphData graphData = graphQueryDomainService.queryEdgesByCondition(edgeSearchRequest);
            GraphDataDTO graphDataDTO = GraphDataDTOConvertor.INSTANCE.graphData2GraphDataDTO(graphData);
            return graphDataDTO;
        } catch (Exception ex) {
            log.error(ex.getMessage(), ex);
            throw new ApplicationException(ErrCodeEnum.EXECUTE_GRAPH_QUERY_ERROR.getErrCode(), ex.getMessage(),ex);
        }
    }

    @Override
    public List<GraphDataDTO.CypherResultTableRow> queryByCypherWithTableData(String spaceName, String cypher,Long fileId) throws ApplicationException {
        try {
            GraphData graphData = graphQueryDomainService.queryByCypher(GraphFieldEnums.GRAPH_SPACENAME_PREFIX + spaceName, cypher,fileId);
            log.info("graphData: {}", JSON.toJSONString(graphData));
            GraphDataDTO graphDataDTO = GraphDataDTOConvertor.INSTANCE.graphData2GraphDataDTO(graphData);
            graphDataDTO.parseRawResult2TableRow(graphData.getRawResult());
            return graphDataDTO.getTableRows();
        } catch (Exception ex) {
            log.error(ex.getMessage(), ex);
            throw new ApplicationException(ErrCodeEnum.EXECUTE_GRAPH_QUERY_ERROR.getErrCode(), ex.getMessage(), ex);
        }
    }

    @Override
    public List<NodeDataDTO> queryNodesByIds(NodeBatchSearchRequest nodeBatchSearchRequest) throws ApplicationException {
        try {
            String cypher = "match (v) where " +
                    nodeBatchSearchRequest.getIds().stream().map(i -> " id(v) == '" + i + "' ")
                            .collect(Collectors.joining("or")) + " return v limit 500";
            List<NodeData> nodeList = graphQueryDomainService.queryNodesByIds(GraphFieldEnums.GRAPH_SPACENAME_PREFIX + nodeBatchSearchRequest.getSpaceName(), cypher);
            List<NodeDataDTO> nodeDataDTOList = NodeDataDTOConvertor.INSTANCE.nodeDataList2NodeDataDTOList(nodeList);
            return nodeDataDTOList;
        } catch (Exception ex) {
            log.error(ex.getMessage(), ex);
            throw new ApplicationException(ErrCodeEnum.EXECUTE_GRAPH_QUERY_ERROR.getErrCode(), ErrCodeEnum.EXECUTE_GRAPH_QUERY_ERROR.getErrMsg());
        }
    }

    @Override
    public List<KeywordDTO> keywordSearch(KeywordSearchRequest keywordSearch) {
        List<Keyword> keywords = graphQueryDomainService.keywordSearch(keywordSearch);
        return BeanUtil.copyToList(keywords,KeywordDTO.class);
    }

    @Override
    public Map<Long, GraphInstanceDTO> instance(String spaceName, List<Long> fileIds) {
        List<GraphInstance> instances = graphQueryDomainService.instance(spaceName, fileIds);
        Map<Long, GraphInstanceDTO> resultMap = Maps.newHashMap();
        instances.forEach(instance -> resultMap.put(instance.getFileId(),BeanUtil.copyProperties(instance,GraphInstanceDTO.class)));
        return resultMap;
    }

    @Override
    public List<NodeDTO> nodes(String spaceName,Long fileId) {
        List<NodeDTO> nodeDTOS = Lists.newArrayList();
        List<NodeDTO.NodeProperty> nodePropertyList = graphQueryDomainService.nodeProperties(spaceName, GraphEnums.NODE_TYPE_NAME);
        Set<String> nodeTypes = graphQueryDomainService.nodeTypes(spaceName,GraphEnums.NODE_TYPE_NAME,fileId);
        nodeTypes.forEach(type -> {
            NodeDTO nodeDTO = new NodeDTO();
            nodeDTO.setNodeType(type);
            nodeDTO.setProperties(nodePropertyList);
            nodeDTOS.add(nodeDTO);
        });
        return nodeDTOS;
    }

    @Override
    public List<EdgeDTO> edges(String spaceName,Long fileId) {
        String edgeType = EDGE_TYPE_NAME;
        List<EdgeDTO.EdgeProperty> edgeProperties = graphQueryDomainService.edgeProperties(spaceName, edgeType);
        Set<String> edgeTypes = graphQueryDomainService.edgeTypes(spaceName,edgeType,fileId);
        List<EdgeDTO> edgeDTOS = Lists.newArrayList();
        edgeTypes.forEach(type -> {
            EdgeDTO edgeDTO = new EdgeDTO();
            edgeDTO.setEdgeType(type);
            edgeDTO.setProperties(edgeProperties);
            edgeDTOS.add(edgeDTO);
        });
        return edgeDTOS;
    }

    @Override
    public GraphDataDTO searchByFile(String spaceName, Long fileId, Integer pageNum) {
        try {
            GraphData graphData = graphQueryDomainService.searchByFile(spaceName,fileId,pageNum);
            GraphDataDTO graphDataDTO = GraphDataDTOConvertor.INSTANCE.graphData2GraphDataDTO(graphData);
            return graphDataDTO;
        } catch (Exception ex) {
            log.error(ex.getMessage(), ex);
            throw new ApplicationException(ErrCodeEnum.EXECUTE_GRAPH_QUERY_ERROR.getErrCode(), ex.getMessage(),ex);
        }
    }
}
