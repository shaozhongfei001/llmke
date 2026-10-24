package com.gientech.raggraphservice.application.service;
import com.gientech.ragcommon.graph.dto.GraphDataDTO;
import com.gientech.ragcommon.graph.dto.NeighbourNodeDTO;
import com.gientech.ragcommon.graph.dto.PathDTO;
import com.gientech.ragcommon.graph.request.CommonNeighbourRequest;
import com.gientech.ragcommon.graph.request.NodeStepSearchRequest;
import com.gientech.ragcommon.graph.request.PathSearchRequest;
import com.gientech.ragcommon.graph.request.WholeGraphSearchRequest;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;

import java.util.List;

/**
 * @Description:
 * @Author: chenjuan
 * @Date: 2023/2/21 16:22
 */
public interface GraphSearchAppService {

    GraphDataDTO searchNodeOneStep(NodeStepSearchRequest nodeStepSearchRequest) ;

    GraphDataDTO wholeGraphSearch(WholeGraphSearchRequest wholeGraphSearchRequest);

    /**
     * 能否展开节点1度关系
     *
     * @param spaceName
     * @param nodeType
     * @param nodeInstanceId
     * @return
     */
    Boolean canSearchNodeOneStep(String spaceName, String nodeType, String nodeInstanceId) throws ApplicationException;

    /**
     * 共通邻居查询
     *
     * @param commonNeighbourRequest
     * @return
     * @throws ApplicationException
     */
    List<NeighbourNodeDTO> commonNeighbourSearch(CommonNeighbourRequest commonNeighbourRequest) throws ApplicationException;

    List<PathDTO> pathSearch(PathSearchRequest pathSearchRequest) throws Exception;

    /**
     * 查询子图
     * @param spaceName
     * @return
     */
    GraphDataDTO subGraph(String spaceName);
}
