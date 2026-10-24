package com.gientech.ragindexservice.infrastructure.threadpool.runnable;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.gientech.ragcommon.index.enmus.ReEmbeddingTaskEnums;
import com.gientech.ragcommon.index.request.FilesParseReq;
import com.gientech.ragindexservice.application.mq.payload.ReParseFilePayload;
import com.gientech.ragindexservice.application.mq.payload.RetryPayload;
import com.gientech.ragindexservice.application.service.KnowledgeBaseListAppService;
import com.gientech.ragindexservice.domain.service.ReEmbeddingFileService;
import lombok.Data;
import lombok.Getter;
import lombok.extern.slf4j.Slf4j;

import java.util.concurrent.CompletableFuture;

/**
 * @author: shirleychen
 * @date 2025/12/4 14:12
 * @description
 */
@Slf4j
@Data
public class ReParseFileRunnable implements Runnable {
    private final KnowledgeBaseListAppService knowledgeBaseListAppService;
    private final RetryPayload reParseFilePayload;
    @Getter
    private final CompletableFuture<Void> future;
    private final ReEmbeddingFileService reEmbeddingFileService;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public ReParseFileRunnable(KnowledgeBaseListAppService knowledgeBaseListAppService, RetryPayload reParseFilePayload, CompletableFuture<Void> future, ReEmbeddingFileService reEmbeddingFileService) {
        this.knowledgeBaseListAppService = knowledgeBaseListAppService;
        this.reParseFilePayload = reParseFilePayload;
        this.future = future;
        this.reEmbeddingFileService = reEmbeddingFileService;
    }


    @Override
    public void run() {
        try {
            ReParseFilePayload payload = (ReParseFilePayload) reParseFilePayload;
            FilesParseReq innerCallReq = FilesParseReq.getInnerCallReq(payload.getKbId(), payload.getKbName(), payload.getFile(), payload.getUserName(), payload.getUserId());
            log.info("reParseFileRunnable filesParseNew params:{}", objectMapper.writeValueAsString(innerCallReq));

            Boolean sendOk = knowledgeBaseListAppService.filesParseNew(innerCallReq);
            if (sendOk) {
                reEmbeddingFileService.markStatus(payload.getTaskFileId(), ReEmbeddingTaskEnums.PROCESSED);
                future.complete(null);
            } else {
                throw new RuntimeException("reParseFileRunnable execute filesParseNew failed");
            }
        } catch (Throwable e) {
            log.error("reParseFileRunnable threw exception", e);
            future.completeExceptionally(e);
        }
    }
}
