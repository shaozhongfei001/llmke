package com.gientech.ragindexservice.infrastructure.threadpool.runnable;

import com.gientech.ragindexservice.application.mq.payload.RetryPayload;
import com.gientech.ragindexservice.application.service.ReEmbeddingAppService;
import lombok.Getter;

import java.util.concurrent.CompletableFuture;

/**
 * @author: shirleychen
 * @date 2025/12/1 18:05
 * @description
 */
public class ReEmbeddingChunkRunnable implements Runnable {

    private final ReEmbeddingAppService reEmbeddingAppService;
    @Getter
    private final RetryPayload reEmbeddingChunkPayload;
    @Getter
    private final CompletableFuture<Void> future;

    public ReEmbeddingChunkRunnable(ReEmbeddingAppService reEmbeddingAppService, RetryPayload payload, CompletableFuture<Void> future) {
        this.reEmbeddingAppService = reEmbeddingAppService;
        this.reEmbeddingChunkPayload = payload;
        this.future = future;
    }

    @Override
    public void run() {
        try {
            reEmbeddingAppService.reEmbeddingChunk(reEmbeddingChunkPayload);
            future.complete(null);
        } catch (Throwable e) {
            future.completeExceptionally(e);
        }
    }
}
