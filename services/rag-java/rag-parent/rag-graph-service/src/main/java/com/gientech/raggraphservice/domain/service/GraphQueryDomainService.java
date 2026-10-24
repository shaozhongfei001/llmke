package com.gientech.raggraphservice.domain.service;


import com.gientech.ragcommon.graph.dto.EdgeDTO;
import com.gientech.ragcommon.graph.dto.GraphInstanceDTO;
import com.gientech.ragcommon.graph.dto.NodeDTO;
import com.gientech.ragcommon.graph.entity.GraphData;
import com.gientech.ragcommon.graph.entity.GraphInstance;
import com.gientech.ragcommon.graph.entity.Keyword;
import com.gientech.ragcommon.graph.entity.NodeData;
import com.gientech.ragcommon.graph.request.EdgeSearchRequest;
import com.gientech.ragcommon.graph.request.KeywordSearchRequest;
import com.gientech.ragcommon.graph.request.NodeSearchRequest;
import com.gientech.ragcommon.infrastructure.exception.DomainException;

import java.util.List;
import java.util.Map;
import java.util.Set;

public interface GraphQueryDomainService {

    /**
     * @param nodeSearchRequest
     * @return
     * @throws DomainException
     */
    GraphData queryNodesByCondition(NodeSearchRequest nodeSearchRequest) throws DomainException;

    /**
     * @param edgeSearchRequest
     * @return
     * @throws DomainException
     */
    GraphData queryEdgesByCondition(EdgeSearchRequest edgeSearchRequest) throws DomainException;

    GraphData queryByCypher(String spaceName, String cypher,Long fileId) throws DomainException;

    List<NodeData> queryNodesByIds(String spaceName, String cypher) throws DomainException;

    List<Keyword> keywordSearch(KeywordSearchRequest keywordSearchRequest);

    List<GraphInstance> instance(String spaceName, List<Long> fileIds);

    List<String> nodes(String spaceName);

    List<NodeDTO.NodeProperty> nodeProperties(String spaceName, String nodeType);

    List<String> edges(String spaceName);

    List<EdgeDTO.EdgeProperty> edgeProperties(String spaceName, String edgeType);

    Set<String> nodeTypes(String spaceName, String nodeType, Long fileId);

    Set<String> edgeTypes(String spaceName, String edgeType, Long fileId);

    GraphData searchByFile(String spaceName, Long fileId, Integer pageNum);
}
