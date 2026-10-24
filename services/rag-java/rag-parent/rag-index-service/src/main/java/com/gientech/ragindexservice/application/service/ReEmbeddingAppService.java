package com.gientech.ragindexservice.application.service;

import com.gientech.ragindexservice.application.mq.payload.RetryPayload;

/**
 * @author: shirleychen
 * @date 2025/12/1 16:33
 * @description
 */
public interface ReEmbeddingAppService {

    void processFile(RetryPayload processFilePayload);

    void reEmbeddingChunk(RetryPayload reEmbeddingChunkPayload);
}
