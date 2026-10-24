package com.gientech.ragindexservice.domain.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.gientech.ragcommon.index.enmus.ReEmbeddingTaskEnums;
import com.gientech.ragindexservice.domain.mapper.ReEmbeddingFileMapper;
import com.gientech.ragindexservice.domain.model.ReEmbeddingFileDO;
import com.gientech.ragindexservice.domain.service.ReEmbeddingFileService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;

import java.util.Collections;
import java.util.List;

/**
 * @author shirleychen
 * @description 针对表【re_embedding_file】的数据库操作Service实现
 * @createDate 2025-12-12 16:51:38
 */
@Service
@Slf4j
public class ReEmbeddingFileServiceImpl extends ServiceImpl<ReEmbeddingFileMapper, ReEmbeddingFileDO>
        implements ReEmbeddingFileService {

    /**
     * 只负责插入，不做查询逻辑
     */
    @Override
    public ReEmbeddingFileDO saveReEmbeddingFile(Long taskId, Long kbId, Long fileId, String kbName) {
        ReEmbeddingFileDO entity = new ReEmbeddingFileDO();
        entity.setTaskId(taskId);
        entity.setKbId(kbId);
        entity.setKbName(kbName);
        entity.setFileId(fileId);
        save(entity);
        return entity;
    }

    @Override
    public ReEmbeddingFileDO getReEmbeddingFile(Long taskId, Long kbId, Long fileId, String kbName) {
        // 查找或创建
        LambdaQueryWrapper<ReEmbeddingFileDO> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(ReEmbeddingFileDO::getTaskId, taskId)
                .eq(ReEmbeddingFileDO::getKbId, kbId)
                .eq(ReEmbeddingFileDO::getFileId, fileId);

        return getOneOpt(wrapper).orElseGet(() -> createIfAbsent(taskId, kbId, kbName, fileId, wrapper));
    }

    private ReEmbeddingFileDO createIfAbsent(Long taskId, Long kbId, String kbName, Long fileId,
                                             LambdaQueryWrapper<ReEmbeddingFileDO> wrapper) {
        try {
            return saveReEmbeddingFile(taskId, kbId, fileId, kbName);
        } catch (DuplicateKeyException e) {
            log.info("ReEmbeddingFile 已存在, 并发创建冲突, taskId={}, kbId={}, fileId={}",
                    taskId, kbId, fileId, e);
            return getOne(wrapper);
        }
    }


    @Override
    public boolean addTotalChunkNum(Long id, Long currentChunkNum) {
        return this.lambdaUpdate().eq(ReEmbeddingFileDO::getId, id).setSql("total_chunk_num = total_chunk_num +" + currentChunkNum).update();
    }

    @Override
    public boolean addErrorChunkNum(Long id, int currentErrChunkNum) {
        return this.lambdaUpdate().eq(ReEmbeddingFileDO::getId, id).set(ReEmbeddingFileDO::getStatus, ReEmbeddingTaskEnums.PARSED_FAIL.getCode()).setSql(String.format("error_chunk_num = error_chunk_num + %s", currentErrChunkNum)).update();
    }

    @Override
    public boolean addProcessedChunkNum(Long id, int currentProcessedNum) {
        return this.lambdaUpdate().eq(ReEmbeddingFileDO::getId, id).setSql(String.format("processed_chunk_num = processed_chunk_num + %s", currentProcessedNum)).update();
    }

    @Override
    public boolean clearChunkNum(Long id) {
        return this.lambdaUpdate().eq(ReEmbeddingFileDO::getId, id).set(ReEmbeddingFileDO::getErrorChunkNum, 0L).set(ReEmbeddingFileDO::getTotalChunkNum, 0L).set(ReEmbeddingFileDO::getProcessedChunkNum, 0L).update();
    }

    @Override
    public boolean markStatus(Long id, ReEmbeddingTaskEnums status) {
        return this.lambdaUpdate().eq(ReEmbeddingFileDO::getId, id).set(ReEmbeddingFileDO::getStatus, status.getCode()).update();
    }

    @Override
    public boolean markStatus(Long kbId, Long taskId, Long fileId, ReEmbeddingTaskEnums status) {
        return this.lambdaUpdate().eq(ReEmbeddingFileDO::getKbId, kbId).eq(ReEmbeddingFileDO::getTaskId, taskId).eq(ReEmbeddingFileDO::getFileId, fileId).eq(ReEmbeddingFileDO::getIsDel, 0).set(ReEmbeddingFileDO::getStatus, status.getCode()).update();
    }

    @Override
    public boolean markMigrated(Long id) {
        return this.lambdaUpdate().eq(ReEmbeddingFileDO::getId, id).set(ReEmbeddingFileDO::getIsMigrate, 1).update();
    }

    @Override
    public boolean setLastError(Long id, String lastError) {
        return this.lambdaUpdate().eq(ReEmbeddingFileDO::getId, id).set(ReEmbeddingFileDO::getLastError, lastError).update();
    }

    @Override
    public boolean setLastError(Long kbId, Long taskId, Long fileId, String lastError) {
        return this.lambdaUpdate().eq(ReEmbeddingFileDO::getKbId, kbId).eq(ReEmbeddingFileDO::getTaskId, taskId).eq(ReEmbeddingFileDO::getFileId, fileId).eq(ReEmbeddingFileDO::getIsDel, 0).set(ReEmbeddingFileDO::getLastError, lastError).update();
    }

    @Override
    public boolean markBatchFileStatus(Long taskId, List<Long> fileIds, ReEmbeddingTaskEnums status) {
        return this.lambdaUpdate().eq(ReEmbeddingFileDO::getTaskId, taskId).in(ReEmbeddingFileDO::getFileId, fileIds).eq(ReEmbeddingFileDO::getIsDel, 0).set(ReEmbeddingFileDO::getStatus, status.getCode()).update();
    }

    @Override
    public List<Long> getFileIdsByTaskId(Long taskId, Long kbId) {
        List<Long> fileIds = this.lambdaQuery().select(ReEmbeddingFileDO::getFileId)
                .eq(ReEmbeddingFileDO::getTaskId, taskId)
                .eq(ReEmbeddingFileDO::getKbId, kbId)
                .eq(ReEmbeddingFileDO::getIsDel, 0)
                .eq(ReEmbeddingFileDO::getStatus, ReEmbeddingTaskEnums.PARSED_SUCCESS.getCode())
                .eq(ReEmbeddingFileDO::getIsMigrate, 0)
                .gt(ReEmbeddingFileDO::getTotalChunkNum, 0)
                .list()
                .stream()
                .map(ReEmbeddingFileDO::getFileId)
                .toList();
        return CollectionUtils.isEmpty(fileIds) ? Collections.emptyList() : fileIds;
    }

    @Override
    public int getNonProcessedFileCount(Long taskId, Long kbId) {
        return getBaseMapper().getNonProcessedFileCount(taskId, kbId);
    }
}




