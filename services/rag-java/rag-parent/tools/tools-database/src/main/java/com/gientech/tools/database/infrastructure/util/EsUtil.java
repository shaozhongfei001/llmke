package com.gientech.tools.database.infrastructure.util;

import com.gientech.ragcommon.index.response.PyEsResponse;
import com.gientech.tools.database.application.remote.EsClient;
import com.gientech.tools.database.interfaces.request.EsDelColRequest;
import com.gientech.tools.database.interfaces.request.EsDelRequest;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpStatus;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Component;

import java.util.List;

import static com.gientech.ragcommon.qa.constant.AIConstant.DB_PREFIX;

/**
 * @author: shirleychen
 * @date 2025/9/16 17:33
 * @description
 */
@Component
@Slf4j
public class EsUtil {
    @Autowired
    private EsClient esClient;

    @Async("asyncExecutor")
    public void delIndex(Long databaseId) {
        EsDelRequest delRequest = new EsDelRequest();
        delRequest.setIndexName(DB_PREFIX + databaseId);
        try {
            PyEsResponse<Object> pyEsResponse = esClient.delIndex(delRequest);
            if (pyEsResponse.getCode().equals(HttpStatus.OK.value())) {
                log.info("db{} es index delete ok", databaseId);
            } else {
                log.error("db{} es index delete error", databaseId);
            }
        } catch (Exception e) {
            log.error(e.getMessage(), e);
        }
    }

    @Async("asyncExecutor")
    public void delDocByCol(String physicalName, Long databaseId) {
        EsDelColRequest delColRequest = new EsDelColRequest();
        delColRequest.setIndexName(DB_PREFIX + databaseId);
        EsDelColRequest.ConditionJson conditionJson = new EsDelColRequest.ConditionJson();
        conditionJson.setPhysicalName(List.of(physicalName));
        delColRequest.setConditionJson(List.of(conditionJson));

        try {
            PyEsResponse<Object> pyEsResponse = esClient.delDocByCol(delColRequest);
            if (pyEsResponse.getCode().equals(HttpStatus.OK.value())) {
                log.info("db{} delete es index by col {} ok", databaseId, physicalName);
            } else {
                log.error("db{} delete es index by col error", databaseId);
            }
        } catch (Exception e) {
            log.error(e.getMessage(), e);
        }
    }
}
