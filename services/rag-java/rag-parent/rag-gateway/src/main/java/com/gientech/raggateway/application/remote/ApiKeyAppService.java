package com.gientech.raggateway.application.remote;

import com.gientech.ragcommon.feign.FeignCustomConfig;
import com.gientech.ragcommon.global.CommonResponse;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;

@FeignClient(name="rag-qa-service", path = "qa/apiKey",configuration = FeignCustomConfig.class)
public interface ApiKeyAppService {

    /**
     * 校验API是否合法
     * @param apiKey
     * @return
     */
    @PostMapping("/checkApiKey")
    Boolean checkApiKey(@RequestParam("apiKey") String apiKey);
}
