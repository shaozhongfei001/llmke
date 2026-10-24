package com.gientech.tools.database.application.remote;

import com.gientech.ragcommon.feign.FeignCustomConfig;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;

/**
 * @author: shirleychen
 * @date 2025/9/17 17:20
 * @description
 */
@FeignClient(name = "rag-qa-service", path = "qa/search/config", configuration = FeignCustomConfig.class)
public interface DatabaseConfigClient {
    @GetMapping("/updateDbIndex")
    int updateDbIndex(@RequestParam("dbIndex") String dbIndex);

    @GetMapping("/renameDbIndex")
    int renameDbIndex(@RequestParam("dbIndex") String dbIndex, @RequestParam("newDbLabel") String newDbLabel, @RequestParam("oldDbLabel") String oldDbLabel);
}
