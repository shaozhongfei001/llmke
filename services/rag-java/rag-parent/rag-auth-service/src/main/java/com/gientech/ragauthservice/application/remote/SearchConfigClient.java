package com.gientech.ragauthservice.application.remote;

import com.gientech.ragcommon.global.CommonResponse;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;

/**
 * @Desc
 * @Author ZhenPanHong
 * @Date 2025/3/26 18:30
 */
@FeignClient(name = "rag-qa-service", path = "qa")
public interface SearchConfigClient {

    @GetMapping("/api/search/config/queryCreator")
    CommonResponse<String> querySearchConfigCreator(@RequestParam(value = "id") Long id);

    @GetMapping("/search/config/transferProperty")
    CommonResponse<Boolean> transferSearchConfigProperty(@RequestParam("owner") String owner, @RequestParam("receiver") String receiver) throws Exception;

}
