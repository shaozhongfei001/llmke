package com.gientech.sensitivewordsservice.application.remote;

import com.gientech.ragcommon.feign.FeignCustomConfig;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;

/**
 * @Description:
 * @Author: chenjuan
 * @Date: 2024/9/10 18:47
 */
@FeignClient(name = "rag-qa-service", path = "qa/search/config", configuration = FeignCustomConfig.class)
public interface SearchConfigClient {
    @GetMapping("/updateSensitiveWord/{id}")
    int updateSensitiveWord(@PathVariable("id") Long wordId);
}
