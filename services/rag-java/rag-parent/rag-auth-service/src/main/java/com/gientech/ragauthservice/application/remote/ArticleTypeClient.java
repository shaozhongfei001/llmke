package com.gientech.ragauthservice.application.remote;

import com.gientech.ragcommon.global.CommonResponse;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;


@FeignClient(name = "intelbrain-dw",path = "dw")
public interface ArticleTypeClient {

    @GetMapping("/api/articleType/queryCreator")
    CommonResponse<String> queryCreator(@RequestParam(value = "id") Long id);
}
