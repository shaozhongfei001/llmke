package com.gientech.ragqaservice.application.remote;

import com.gientech.ragqaservice.interfaces.dto.RetrieveData;
import com.gientech.ragqaservice.interfaces.req.app.RetrieveDocReq;
import com.gientech.ragqaservice.interfaces.resp.LLMClientResp;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;

/**
 * @author shirleychen
 */

@FeignClient(name = "retrieve-service",url = "${spring.ai.gt.retrieve-url}")
public interface RetrieveClient {

    @PostMapping("/retrieval_documents")
    LLMClientResp<RetrieveData> retrievalDocuments(@RequestBody RetrieveDocReq request);
}
