package com.gientech.ragindexservice.domain.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.gientech.ragindexservice.application.mq.payload.RetryPayload;
import com.gientech.ragindexservice.domain.entity.ReEmbeddingRetryTask;
import com.gientech.ragindexservice.domain.model.ReEmbeddingRetryTaskDO;

/**
 * @author shirleychen
 * @description 针对表【re_embedding_retry_task】的数据库操作Service
 * @createDate 2025-11-28 14:35:41
 */
public interface ReEmbeddingRetryTaskService extends IService<ReEmbeddingRetryTaskDO> {

    ReEmbeddingRetryTaskDO saveRetryTask(RetryPayload payload, String lastError, Integer type);

    ReEmbeddingRetryTask getRetryTask();

    boolean incrRetryTimes(Long retryTaskId);

    void updateStatus(Long retryTaskId, Integer status, String lastError);

    void updateStatus(Long taskId, Long fileId, Integer status, String lastError);
}
