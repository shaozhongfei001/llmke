package com.gientech.ragindexservice.domain.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.gientech.ragcommon.index.enmus.ReEmbeddingTaskEnums;
import com.gientech.ragindexservice.domain.model.ReEmbeddingFileDO;

import java.util.List;

/**
 * @author shirleychen
 * @description 针对表【re_embedding_file】的数据库操作Service
 * @createDate 2025-12-12 16:51:38
 */
public interface ReEmbeddingFileService extends IService<ReEmbeddingFileDO> {

    ReEmbeddingFileDO saveReEmbeddingFile(Long taskId, Long kbId, Long fileId, String kbName);

    ReEmbeddingFileDO getReEmbeddingFile(Long taskId, Long kbId, Long fileId, String kbName);

    boolean addTotalChunkNum(Long taskId, Long currentChunkNum);

    boolean addErrorChunkNum(Long taskId, int currentErrChunkNum);

    boolean addProcessedChunkNum(Long taskId, int currentProcessedNum);

    boolean clearChunkNum(Long id);

    boolean markStatus(Long id, ReEmbeddingTaskEnums status);

    boolean markStatus(Long kbId, Long taskId, Long fileId, ReEmbeddingTaskEnums status);

    boolean markMigrated(Long id);

    boolean setLastError(Long id, String lastError);

    boolean setLastError(Long kbId, Long taskId, Long fileId, String lastError);

    boolean markBatchFileStatus(Long taskId, List<Long> fileIds, ReEmbeddingTaskEnums status);

    List<Long> getFileIdsByTaskId(Long taskId, Long kbId);

    int getNonProcessedFileCount(Long taskId, Long kbId);
}
