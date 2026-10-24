package com.gientech.ragqaservice.application.convertor;

import com.gientech.ragqaservice.application.service.entity.AiHistory;
import com.gientech.ragqaservice.domain.entity.History;
import org.mapstruct.Mapper;
import org.mapstruct.Mapping;
import org.mapstruct.factory.Mappers;

import java.util.List;

@Mapper
public interface HistoryConvertor {
    HistoryConvertor INSTANCE = Mappers.getMapper(HistoryConvertor.class);

    @Mapping(source = "queryContent", target = "query")
    AiHistory history2AiHistory(History history);

    List<AiHistory> histories2AiHistories(List<History> histories);
}
