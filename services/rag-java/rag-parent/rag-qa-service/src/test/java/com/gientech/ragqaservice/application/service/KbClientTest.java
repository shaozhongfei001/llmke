package com.gientech.ragqaservice.application.service;

import com.alibaba.fastjson2.JSON;
import com.fasterxml.jackson.databind.JsonNode;
import com.gientech.ragcommon.index.request.PageFileStreamReq;
import com.gientech.ragcommon.index.utils.JSONPagination;
import com.gientech.ragqaservice.application.remote.KbClient;
import com.gientech.start.storage.exception.FileStorageException;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.ResponseEntity;

import java.io.IOException;

/**
 * @author: shirleychen
 * @date 2025/9/3 16:06
 * @description
 */
@SpringBootTest
public class KbClientTest {
    @Autowired
    private KbClient kbClient;

    @Test
    public void testKbClient() throws IOException, FileStorageException {
        ResponseEntity<JSONPagination.PageResult<JsonNode>> responseEntity = kbClient.pageFileStream(PageFileStreamReq.from("http://10.15.12.13:9000/dev-rag-data/retrieve-sql-data/test_data.json", false));
        JSONPagination.PageResult<JsonNode> body = responseEntity.getBody();
        System.out.println(JSON.toJSONString(body.getData()));
    }
}
