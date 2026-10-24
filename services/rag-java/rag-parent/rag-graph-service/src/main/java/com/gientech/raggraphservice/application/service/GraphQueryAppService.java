package com.gientech.raggraphservice.application.service;

import com.gientech.ragcommon.graph.dto.*;
import com.gientech.ragcommon.graph.request.EdgeSearchRequest;
import com.gientech.ragcommon.graph.request.KeywordSearchRequest;
import com.gientech.ragcommon.graph.request.NodeBatchSearchRequest;
import com.gientech.ragcommon.graph.request.NodeSearchRequest;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;

import java.util.List;
import java.util.Map;

public interface GraphQueryAppService {

    /**
     * 节点查询
     * @param nodeSearchRequest
     * @return
     * @throws ApplicationException
     */
    GraphDataDTO queryNodesByCondition(NodeSearchRequest nodeSearchRequest) throws ApplicationException;

    /**
     * 边查询
     * @param edgeSearchRequest
     * @return
     * @throws ApplicationException
     */
    GraphDataDTO queryEdgesByCondition(EdgeSearchRequest edgeSearchRequest) throws ApplicationException;

    /**
     * 语句查询，包含表格形式返回的数据
     *
     * @param spaceName
     * @param cypher
     * @return
     * @throws ApplicationException
     */
    List<GraphDataDTO.CypherResultTableRow> queryByCypherWithTableData(String spaceName, String cypher,Long fileId) throws ApplicationException;

    /**
     * 根据vid批量查询节点
     * @param nodeBatchSearchRequest
     * @return
     * @throws ApplicationException
     */
    List<NodeDataDTO> queryNodesByIds(NodeBatchSearchRequest nodeBatchSearchRequest) throws ApplicationException;

    /**
     * 关键字提示查询
     * @param keywordSearch
     * @return
     */
    List<KeywordDTO> keywordSearch(KeywordSearchRequest keywordSearch);

    /**
     * 查询点和边的实例数
     * @param spaceName
     * @param fileIds
     * @return
     */
    Map<Long, GraphInstanceDTO> instance(String spaceName, List<Long> fileIds);

    /**
     * 查询点以及属性
     * @param spaceName
     * @return
     */
    List<NodeDTO> nodes(String spaceName,Long fileId);

    /**
     * 查询边以及属性
     * @param spaceName
     * @return
     */
    List<EdgeDTO> edges(String spaceName,Long fileId);

    /**
     * 通过文件id和页码查询数据
     * @param spaceName
     * @param fileId
     * @param pageNum
     * @return
     */
    GraphDataDTO searchByFile(String spaceName, Long fileId, Integer pageNum);
}
