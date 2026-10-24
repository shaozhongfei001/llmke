package com.gientech.ragindexservice.domain.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.gientech.ragcommon.index.dto.ModelSimpDTO;
import com.gientech.ragcommon.index.enmus.ReEmbeddingTaskEnums;
import com.gientech.ragindexservice.domain.model.ReEmbeddingTaskDO;

import java.util.List;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.function.Consumer;

/**
 * @author shirleychen
 * @description 针对表【re_embedding_task】的数据库操作Service
 * @createDate 2025-11-25 15:47:49
 */
public interface ReEmbeddingTaskService extends IService<ReEmbeddingTaskDO> {

    boolean updateStatus(Long taskId, ReEmbeddingTaskEnums status);

    boolean addTotalFileNum(Long taskId, Long currentFileNum);

    boolean markProcessedFile(Long taskId, Integer processedFileNum);

    boolean markErrorFile(Long taskId, Integer processedFileNum);

    Integer getLatestStatus(Long taskId);

    void doMigrate(ThreadPoolExecutor fileProcessExecutor, String kbName, String collectionName, ModelSimpDTO embeddingModelInfo, Long kbId, Long taskId, Consumer<Throwable> failCallback);
}
