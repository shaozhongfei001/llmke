package com.gientech.raggraphservice.application.service.impl;

import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragcommon.graph.dto.GraphDataStatisticsDTO;
import com.gientech.ragcommon.graph.entity.GraphInstance;
import com.gientech.raggraphservice.application.service.GraphDataStatisticsAppService;
import com.gientech.raggraphservice.domain.service.GraphQueryDomainService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import java.util.Arrays;
import java.util.List;
import java.util.Objects;


@Service
@Slf4j
public class GraphDataStatisticsAppServiceImpl implements GraphDataStatisticsAppService {

    @Autowired
    private GraphQueryDomainService graphQueryDomainService;

    @Override
    public GraphDataStatisticsDTO getWholeDataStatistics(String spaceName,Long fileId) {
        List<GraphInstance> instances = graphQueryDomainService.instance(spaceName, Objects.nonNull(fileId) ? Arrays.asList(fileId) : null);
        GraphDataStatisticsDTO graphDataStatisticsDTO = new GraphDataStatisticsDTO();
        graphDataStatisticsDTO.setSpaceName(spaceName);
        graphDataStatisticsDTO.setCreator(UserContext.getUser().getUserName());
        graphDataStatisticsDTO.setNodeInstanceAmount(instances.stream().mapToLong(GraphInstance::getNodeCount).sum());
        graphDataStatisticsDTO.setEdgeInstanceAmount(instances.stream().mapToLong(GraphInstance::getEdgeCount).sum());
        return graphDataStatisticsDTO;
    }
}
