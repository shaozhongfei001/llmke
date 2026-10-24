package com.gientech.ragqaservice.application.remote;


import com.gientech.ragqaservice.application.service.entity.QuestionRecommendRequest;
import com.gientech.ragqaservice.application.service.entity.SqlGenerateRequest;
import com.gientech.ragqaservice.interfaces.resp.LLMClientResp;
import com.gientech.ragqaservice.interfaces.resp.RetrieveSql;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;

@FeignClient(name = "llm-service",url = "${spring.ai.gt.llm-url}")
public interface LlmClient {

    @PostMapping("/llm_question_recommend")
    String[] llmQuestionRecommend(@RequestBody QuestionRecommendRequest request);


    @PostMapping("/llm_sql_generate")
    LLMClientResp<RetrieveSql> llmSqlGenerate(@RequestBody SqlGenerateRequest request);

}
