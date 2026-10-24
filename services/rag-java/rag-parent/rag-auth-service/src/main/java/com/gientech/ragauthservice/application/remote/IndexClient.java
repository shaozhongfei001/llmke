package com.gientech.ragauthservice.application.remote;

import com.gientech.ragcommon.global.CommonResponse;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;

/**
 * @Desc
 * @Author ZhenPanHong
 * @Date 2025/3/26 17:46
 */
@FeignClient(name = "rag-index-service",path = "index")
public interface IndexClient {

    @GetMapping("/api/knowledgeBase/queryCreator")
    CommonResponse<String> queryKbCreator(@RequestParam(value = "id") Long id);

    @GetMapping("/api/knowledgeBase/file/queryCreator")
    CommonResponse<String> queryKbFileCreator(@RequestParam(value = "id") Long id);

    @GetMapping("/folder/queryCreator")
    CommonResponse<String> queryFolderCreator(@RequestParam(value = "id") Long id);

    @GetMapping("/api/modelInfo/queryCreator")
    CommonResponse<String> queryModelCreator(@RequestParam(value = "id") Long id);

    @GetMapping("/database/queryDatabaseCreator/{databaseId}")
    CommonResponse<String> queryDatabaseCreator(@RequestParam(value = "databaseId") Long databaseId);

    @GetMapping("/modelInfo/transferProperty")
    CommonResponse<Boolean> transferModelProperty(@RequestParam("owner") String owner, @RequestParam("receiver") String receiver) throws Exception;

    @GetMapping("/knowledgeBase/transferProperty")
    CommonResponse<Boolean> transferKbProperty(@RequestParam("owner") String owner, @RequestParam("receiver") String receiver) throws Exception;

}
