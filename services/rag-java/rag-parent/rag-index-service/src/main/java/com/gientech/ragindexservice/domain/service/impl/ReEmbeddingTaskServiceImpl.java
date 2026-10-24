package com.gientech.ragindexservice.domain.service.impl;

import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.gientech.ragcommon.index.constant.IndexConstant;
import com.gientech.ragcommon.index.dto.ModelSimpDTO;
import com.gientech.ragcommon.index.enmus.KbFileStatusEnums;
import com.gientech.ragcommon.index.enmus.ReEmbeddingTaskEnums;
import com.gientech.ragcommon.index.response.PyMilvusResponse;
import com.gientech.ragindexservice.application.mq.payload.MilvusMigratePayload;
import com.gientech.ragindexservice.application.remote.PyEsClient;
import com.gientech.ragindexservice.application.remote.PyMilvusClient;
import com.gientech.ragindexservice.application.remote.request.PyCollection;
import com.gientech.ragindexservice.application.service.KnowledgeBaseListAppService;
import com.gientech.ragindexservice.domain.mapper.ReEmbeddingTaskMapper;
import com.gientech.ragindexservice.domain.model.ReEmbeddingFileDO;
import com.gientech.ragindexservice.domain.model.ReEmbeddingTaskDO;
import com.gientech.ragindexservice.domain.service.ReEmbeddingFileService;
import com.gientech.ragindexservice.domain.service.ReEmbeddingTaskService;
import com.gientech.ragindexservice.infrastructure.threadpool.runnable.MilvusMigrateRunnable;
import com.google.common.collect.Lists;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;

import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.function.Consumer;

/**
 * @author shirleychen
 * @description 针对表【re_embedding_task】的数据库操作Service实现
 * @createDate 2025-11-25 15:47:49
 */
@Service
@Slf4j
public class ReEmbeddingTaskServiceImpl extends ServiceImpl<ReEmbeddingTaskMapper, ReEmbeddingTaskDO>
        implements ReEmbeddingTaskService {

    private final PyMilvusClient pyMilvusClient;

    private final PyEsClient pyEsClient;
    private final ReEmbeddingFileService reEmbeddingFileService;
    private final KnowledgeBaseListAppService knowledgeBaseListAppService;

    @Value("${re-embedding.migrate-size:2000}")
    private Integer migrateBatchSize;

    private final ObjectMapper objectMapper = new ObjectMapper();

    public ReEmbeddingTaskServiceImpl(PyEsClient pyEsClient, PyMilvusClient pyMilvusClient, ReEmbeddingFileService reEmbeddingFileService, KnowledgeBaseListAppService knowledgeBaseListAppService) {

        this.pyEsClient = pyEsClient;
        this.pyMilvusClient = pyMilvusClient;
        this.reEmbeddingFileService = reEmbeddingFileService;
        this.knowledgeBaseListAppService = knowledgeBaseListAppService;
    }

    @Override
    public boolean updateStatus(Long taskId, ReEmbeddingTaskEnums status) {
        return this.lambdaUpdate().eq(ReEmbeddingTaskDO::getId, taskId).set(ReEmbeddingTaskDO::getStatus, status.getCode()).update();
    }

    @Override
    public boolean addTotalFileNum(Long taskId, Long currentFileNum) {
        return this.lambdaUpdate().eq(ReEmbeddingTaskDO::getId, taskId).setSql(String.format("total_file_num = total_file_num + %s", currentFileNum)).update();
    }

    @Override
    public boolean markProcessedFile(Long taskId, Integer processedFileNum) {
        log.info("markProcessedFile,taskId={},processedFileNum={}", taskId, processedFileNum);
        return this.lambdaUpdate().eq(ReEmbeddingTaskDO::getId, taskId).setSql(String.format("processed_file_num = processed_file_num + %s", processedFileNum)).update();
    }

    @Override
    public boolean markErrorFile(Long taskId, Integer processedFileNum) {
        return this.lambdaUpdate().eq(ReEmbeddingTaskDO::getId, taskId).setSql(String.format("error_file_num = error_file_num + %s", processedFileNum)).update();
    }

    @Override
    public Integer getLatestStatus(Long taskId) {
        return this.lambdaQuery().select(ReEmbeddingTaskDO::getStatus).eq(ReEmbeddingTaskDO::getId, taskId).eq(ReEmbeddingTaskDO::getIsDel, 0).one().getStatus();
    }


    @Override
    public void doMigrate(ThreadPoolExecutor fileProcessExecutor, String kbName, String collectionName, ModelSimpDTO embeddingModelInfo, Long kbId, Long taskId, Consumer<Throwable> failCallback) {
        List<Long> parsedFileIds = reEmbeddingFileService.getFileIdsByTaskId(taskId, kbId);
        log.info("parsedFileIds={}", parsedFileIds);
        List<String> collectionNames = IndexConstant.getCollectionNames(kbName);
        List<String> newCollectionNames = IndexConstant.getNewCollectionNames(kbName + "_" + taskId);
        for (int i = 0; i < collectionNames.size(); i++) {
            String oldCollectionName = collectionNames.get(i);
            String newCollectionName = newCollectionNames.get(i);
            PyCollection oldCollectionParam = new PyCollection(oldCollectionName);
            PyMilvusResponse<Object> delMilvusResponse = pyMilvusClient.delDocByCol(oldCollectionParam);
            try {
                log.info("delMilvusResponse {} params:{}", delMilvusResponse, objectMapper.writeValueAsString(oldCollectionParam));
            } catch (JsonProcessingException e) {
                log.error(e.getMessage(), e);
            }
            //创建同旧库名的库
            oldCollectionParam.setModelName(embeddingModelInfo.getModelName());
            PyMilvusResponse<Object> createSameOldCollection = pyMilvusClient.createMilvusCollection(oldCollectionParam);
            try {
                log.info("createSameCollection {}, params:{}", createSameOldCollection, objectMapper.writeValueAsString(oldCollectionParam));
            } catch (JsonProcessingException e) {
                log.error(e.getMessage(), e);
            }
            //新旧库迁移
            doMilvusMigrate(fileProcessExecutor, parsedFileIds, taskId, embeddingModelInfo, newCollectionName, oldCollectionName, kbId, failCallback);
        }
    }

    private void doMilvusMigrate(ThreadPoolExecutor fileProcessExecutor, List<Long> parsedFileIds, Long taskId, ModelSimpDTO embeddingModelInfo, String collectionName, String kbName, Long kbId, Consumer<Throwable> failCallback) {
        List<CompletableFuture<Void>> milvusMigrateFutures = Lists.newArrayList();
        parsedFileIds.forEach(fileId -> {
            ReEmbeddingFileDO reEmbeddingFile = reEmbeddingFileService.getReEmbeddingFile(taskId, kbId, fileId, kbName);
            Long taskFileId = reEmbeddingFile.getId();
            MilvusMigratePayload milvusMigratePayload = new MilvusMigratePayload(taskId, 4, embeddingModelInfo, fileId, collectionName, kbName, kbId, migrateBatchSize, null);
            CompletableFuture<Void> future = new CompletableFuture<>();
            fileProcessExecutor.execute(new MilvusMigrateRunnable(pyMilvusClient, pyEsClient, milvusMigratePayload, future));
            CompletableFuture<Void> safe = future.handle((v, ex) -> {
                try {
                    if (ex != null) {
                        log.error("migrate complete exceptionally");
                        reEmbeddingFileService.setLastError(taskFileId, ex.getMessage());
                        knowledgeBaseListAppService.updateParseStatusByIds(List.of(milvusMigratePayload.getFileId()), KbFileStatusEnums.PARSE_FAIL.getValue(), true);
                        if (failCallback != null) failCallback.accept(ex);
                    } else {
                        reEmbeddingFileService.markMigrated(taskFileId);
                        knowledgeBaseListAppService.updateParseStatusByIds(List.of(milvusMigratePayload.getFileId()), KbFileStatusEnums.PARSE_SUCCESS.getValue(), true);
                    }
                } catch (Throwable t) {
                    // 回调里任何异常都吞掉，避免影响等待
                    log.warn("migrate callback error fileId={}", fileId, t);
                    knowledgeBaseListAppService.updateParseStatusByIds(List.of(milvusMigratePayload.getFileId()), KbFileStatusEnums.PARSE_FAIL.getValue(), true);
                }
                return null;
            });
            milvusMigrateFutures.add(safe);
        });

        if (!CollectionUtils.isEmpty(milvusMigrateFutures)) {
            CompletableFuture.allOf(milvusMigrateFutures.toArray(new CompletableFuture[0])).join();
            delMilvusOfCollectionName(collectionName);
        }

    }

    private void delMilvusOfCollectionName(String collectionName) {
        //删除新库
        log.info("删除新库..{}", collectionName);
        PyCollection pyCollection = new PyCollection(collectionName);
        PyMilvusResponse<Object> delMilvusResponse = pyMilvusClient.delDocByCol(pyCollection);
        try {
            log.info("删除新库...delMilvusResponse {} params:{}", objectMapper.writeValueAsString(delMilvusResponse), objectMapper.writeValueAsString(pyCollection));
        } catch (JsonProcessingException e) {
            log.error(e.getMessage(), e);
        }

    }

}




