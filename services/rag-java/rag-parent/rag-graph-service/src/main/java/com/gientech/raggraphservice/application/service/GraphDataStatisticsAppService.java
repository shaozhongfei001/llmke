package com.gientech.raggraphservice.application.service;

import com.gientech.ragcommon.graph.dto.GraphDataStatisticsDTO;

public interface GraphDataStatisticsAppService {

    GraphDataStatisticsDTO getWholeDataStatistics(String spaceName,Long fileId);

}
