package com.gientech.ragindexservice.infrastructure.threadpool.runnable;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.index.response.PyMilvusResponse;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.ragindexservice.application.mq.payload.MilvusMigratePayload;
import com.gientech.ragindexservice.application.mq.payload.RetryPayload;
import com.gientech.ragindexservice.application.remote.PyEsClient;
import com.gientech.ragindexservice.application.remote.PyMilvusClient;
import com.gientech.ragindexservice.application.remote.request.PyMigrateRequest;
import lombok.Data;
import lombok.Getter;
import lombok.extern.slf4j.Slf4j;

import java.util.Objects;
import java.util.concurrent.CompletableFuture;

/**
 * @author: shirleychen
 * @date 2025/12/5 14:21
 * @description
 */
@Data
@Slf4j
public class MilvusMigrateRunnable implements Runnable {

    private final PyMilvusClient pyMilvusClient;

    private final PyEsClient pyEsClient;

    @Getter
    private final RetryPayload milvusMigratePayload;
    @Getter
    private final CompletableFuture<Void> future;


    public MilvusMigrateRunnable(PyMilvusClient pyMilvusClient, PyEsClient pyEsClient, RetryPayload milvusMigratePayload, CompletableFuture<Void> future) {
        this.pyMilvusClient = pyMilvusClient;
        this.pyEsClient = pyEsClient;
        this.milvusMigratePayload = milvusMigratePayload;
        this.future = future;
    }

    private final ObjectMapper objectMapper = new ObjectMapper();

    @Override
    public void run() {
        try {
            MilvusMigratePayload payload = (MilvusMigratePayload) milvusMigratePayload;
            PyMigrateRequest request = new PyMigrateRequest(payload.getSourceCollection(), payload.getTargetCollection(), payload.getFileId(), payload.getBatchSize());
            log.info("{} 迁移到 {}, MilvusMigrateRequest : {}", payload.getSourceCollection(), payload.getTargetCollection(), objectMapper.writeValueAsString(request));
            PyMilvusResponse<Object> response = pyMilvusClient.migrateMilvusCollection(request);
            if (!Objects.isNull(response) && !response.getCode().equals(200)) {
                future.completeExceptionally(new ApplicationException(ErrCodeEnum.MIGRATE_FAILED.getErrCode(), response.getMsg()));
            }
            log.info("MilvusMigrateRequest: {}, response:{}", objectMapper.writeValueAsString(request), objectMapper.writeValueAsString(response));
            future.complete(null);
        } catch (Throwable e) {
            log.error("MilvusMigrateRunnable", e);
            future.completeExceptionally(e);
        }
    }
}
