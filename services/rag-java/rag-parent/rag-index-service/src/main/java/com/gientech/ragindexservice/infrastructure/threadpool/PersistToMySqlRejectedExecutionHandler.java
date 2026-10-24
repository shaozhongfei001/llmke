package com.gientech.ragindexservice.infrastructure.threadpool;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.index.dto.KnowledgeBaseFileDTO;
import com.gientech.ragcommon.index.enmus.ReEmbeddingTaskEnums;
import com.gientech.ragcommon.index.enmus.RetryTaskEnums;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.ragindexservice.application.mq.payload.*;
import com.gientech.ragindexservice.domain.model.ReEmbeddingRetryTaskDO;
import com.gientech.ragindexservice.domain.service.ReEmbeddingFileService;
import com.gientech.ragindexservice.domain.service.ReEmbeddingRetryTaskService;
import com.gientech.ragindexservice.domain.service.ReEmbeddingTaskService;
import com.gientech.ragindexservice.infrastructure.threadpool.runnable.MilvusMigrateRunnable;
import com.gientech.ragindexservice.infrastructure.threadpool.runnable.ProcessFileRunnable;
import com.gientech.ragindexservice.infrastructure.threadpool.runnable.ReEmbeddingChunkRunnable;
import com.gientech.ragindexservice.infrastructure.threadpool.runnable.ReParseFileRunnable;
import lombok.extern.slf4j.Slf4j;

import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.RejectedExecutionHandler;
import java.util.concurrent.ThreadPoolExecutor;

/**
 * @author: shirleychen
 * @date 2025/12/1 17:35
 * @description
 */
@Slf4j
public class PersistToMySqlRejectedExecutionHandler implements RejectedExecutionHandler {
    private final ReEmbeddingRetryTaskService retryTaskService;
    private final ReEmbeddingTaskService taskService;
    private final ReEmbeddingFileService fileService;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public PersistToMySqlRejectedExecutionHandler(ReEmbeddingRetryTaskService retryTaskService, ReEmbeddingTaskService taskService, ReEmbeddingFileService fileService) {
        this.taskService = taskService;
        this.retryTaskService = retryTaskService;
        this.fileService = fileService;
    }

    @Override
    public void rejectedExecution(Runnable r, ThreadPoolExecutor executor) {
        log.info("进入拒绝策略");
        // 如果线程池已经 shutdown，通常就没必要再持久化了，直接丢弃或记录日志
        if (executor.isShutdown()) {
            log.warn("Task {} rejected because executor is shutdown.", r);
            throw new RejectedExecutionException("Executor is shutdown");
        }

        if (r instanceof ProcessFileRunnable task) {
            ProcessFilePayload processFilePayload = (ProcessFilePayload) task.getRetryPayload();
            task.getFuture().completeExceptionally(new ApplicationException(ErrCodeEnum.TASK_REJECT));
            taskService.updateStatus(processFilePayload.getTaskId(), ReEmbeddingTaskEnums.PARSED_FAIL);
            processFilePayload.setRetry(true);
            saveRetryTask(processFilePayload, "", RetryTaskEnums.FILE.getCode());
        } else if (r instanceof ReEmbeddingChunkRunnable task) {
            ReEmbeddingChunkPayload reEmbeddingChunkPayload = (ReEmbeddingChunkPayload) task.getReEmbeddingChunkPayload();
            task.getFuture().completeExceptionally(new ApplicationException(ErrCodeEnum.TASK_REJECT));
            KnowledgeBaseFileDTO file = reEmbeddingChunkPayload.getFile();
            ProcessFilePayload filePayload = new ProcessFilePayload(reEmbeddingChunkPayload, file);
            filePayload.setRetry(true);
            taskService.updateStatus(reEmbeddingChunkPayload.getTaskId(), ReEmbeddingTaskEnums.PARSED_FAIL);
            saveRetryTask(filePayload, "", RetryTaskEnums.FILE.getCode());
        } else if (r instanceof ReParseFileRunnable task) {
            ReParseFilePayload reParseFilePayload = (ReParseFilePayload) task.getReParseFilePayload();
            task.getFuture().completeExceptionally(new ApplicationException(ErrCodeEnum.TASK_REJECT));
            taskService.updateStatus(reParseFilePayload.getTaskId(), ReEmbeddingTaskEnums.PARSED_FAIL);
            reParseFilePayload.setRetry(true);
            saveRetryTask(reParseFilePayload, "", RetryTaskEnums.REPARSE.getCode());
        } else if (r instanceof MilvusMigrateRunnable task) {
            MilvusMigratePayload milvusMigratePayload = (MilvusMigratePayload) task.getMilvusMigratePayload();
            try {
                log.error("migrate进入拒绝策略:{}", objectMapper.writeValueAsString(milvusMigratePayload));
            } catch (JsonProcessingException e) {
                log.error(e.getMessage(), e);
            }
            fileService.setLastError(milvusMigratePayload.getKbId(), milvusMigratePayload.getTaskId(), milvusMigratePayload.getFileId(), "migrate线程进入拒绝策略");
            task.getFuture().completeExceptionally(new ApplicationException(ErrCodeEnum.TASK_REJECT));
        } else {
            // 不认识的任务类型，保留默认行为
            throw new RejectedExecutionException(
                    "Task " + r + " rejected from " + executor);
        }

    }


    private void saveRetryTask(RetryPayload payload, String lastError, Integer type) {
        try {
            ReEmbeddingRetryTaskDO reEmbeddingRetryTaskDO = retryTaskService.saveRetryTask(payload, lastError, type);
            log.warn("Task rejected and persisted to DB. type={}, payload={}",
                    reEmbeddingRetryTaskDO.getType(), reEmbeddingRetryTaskDO.getPayload());
        } catch (Exception e) {
            // 持久化失败要兜底，不然调用方连异常都不知道
            log.error("Persist rejected task to DB failed, task", e);
            // 让调用方感知失败
            throw new RejectedExecutionException(
                    "Persist rejected task failed", e);
        }
    }


}
