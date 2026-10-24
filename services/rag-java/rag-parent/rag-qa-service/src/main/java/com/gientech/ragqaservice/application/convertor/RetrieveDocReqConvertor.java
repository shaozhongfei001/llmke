package com.gientech.ragqaservice.application.convertor;

import com.gientech.ragqaservice.interfaces.req.app.RetrieveDocReq;
import com.gientech.ragqaservice.interfaces.req.app.RetrieveDocReq4Platform;
import org.mapstruct.Mapper;
import org.mapstruct.factory.Mappers;

@Mapper
public interface RetrieveDocReqConvertor {
    RetrieveDocReqConvertor INSTANCE = Mappers.getMapper(RetrieveDocReqConvertor.class);

    default RetrieveDocReq RetrieveDocReq4Platform2RetrieveDocReq(RetrieveDocReq4Platform req4Platform) {
            RetrieveDocReq retrieveDocReq = new RetrieveDocReq();
            retrieveDocReq.setTopK(req4Platform.getRecallCount());
            retrieveDocReq.setEnabledGraph(req4Platform.getKnowledgeGraphEnable());
            retrieveDocReq.setSearchPolicy(req4Platform.getRetrievalType().getCode());
            retrieveDocReq.setEnabledTableSelect(req4Platform.getTableFilterEnabled());
            retrieveDocReq.setQuery(req4Platform.getUserQuestion());
            retrieveDocReq.setEnabledFaq(req4Platform.getFaqPriority());
            retrieveDocReq.setStream(Boolean.FALSE);
            retrieveDocReq.setKnowledgeBaseName(req4Platform.getKnowledge());
            retrieveDocReq.setEnabledRerank(req4Platform.getRerankerEnabled());
            retrieveDocReq.setScoreThreshold(req4Platform.getSimilarityThreshold());
            RetrieveDocReq.RerankModel rerankModel = new RetrieveDocReq.RerankModel();
            rerankModel.setModelName(req4Platform.getRerankerModel());
            retrieveDocReq.setRerankModelInfo(rerankModel);

            return retrieveDocReq;
    }
}
