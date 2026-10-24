package com.gientech.ragindexservice.infrastructure.threadpool.runnable;

import com.gientech.ragcommon.index.enmus.KbFileStatusEnums;
import com.gientech.ragindexservice.application.mq.payload.RetryPayload;
import com.gientech.ragindexservice.application.service.KnowledgeBaseListAppService;
import com.gientech.ragindexservice.application.service.ReEmbeddingAppService;
import lombok.Getter;
import lombok.extern.slf4j.Slf4j;

import java.util.concurrent.CompletableFuture;

/**
 * @author: shirleychen
 * @date 2025/12/1 17:56
 * @description
 */
@Slf4j
public class ProcessFileRunnable implements Runnable {
    private final ReEmbeddingAppService reEmbeddingAppService;
    @Getter
    private final RetryPayload retryPayload;
    @Getter
    private final CompletableFuture<Void> future;

    public ProcessFileRunnable(ReEmbeddingAppService reEmbeddingAppService,RetryPayload retryPayload, CompletableFuture<Void> future) {
        this.reEmbeddingAppService = reEmbeddingAppService;
        this.retryPayload = retryPayload;
        this.future = future;
    }

    @Override
    public void run() {
        try {
            reEmbeddingAppService.processFile(this.retryPayload);
            future.complete(null);
        } catch (Throwable e) {
            log.error("ProcessFileRunnable exception", e);
            future.completeExceptionally(e);
        }
    }

}
