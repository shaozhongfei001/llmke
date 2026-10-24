package com.gientech.ragindexservice.application.remote;

import com.gientech.ragcommon.feign.FeignCustomConfig;
import com.gientech.ragcommon.qa.dto.DialogDTO;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestParam;


@FeignClient(name = "rag-qa-service", path = "qa/dialogue", configuration = FeignCustomConfig.class)
public interface DialoguaClient {

    @PutMapping(value = "updateQaFiles")
    Boolean updateQaFiles(@RequestParam("queryId") String queryId, @RequestParam("filePaths") String filePaths);


    @GetMapping(value = "getDialogBySessionId")
    DialogDTO getDialogBySessionId(@RequestParam("sessionId") String sessionId);
}
