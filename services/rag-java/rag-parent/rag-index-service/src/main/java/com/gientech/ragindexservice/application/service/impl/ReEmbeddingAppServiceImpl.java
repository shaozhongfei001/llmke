package com.gientech.ragindexservice.application.service.impl;

import com.alibaba.fastjson.JSON;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.index.FileChunkDTO;
import com.gientech.ragcommon.index.constant.IndexConstant;
import com.gientech.ragcommon.index.dto.KnowledgeBaseFileDTO;
import com.gientech.ragcommon.index.dto.ModelSimpDTO;
import com.gientech.ragcommon.index.enmus.KbFileStatusEnums;
import com.gientech.ragcommon.index.enmus.ReEmbeddingTaskEnums;
import com.gientech.ragcommon.index.response.PyMilvusResponse;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.ragindexservice.application.mq.payload.ProcessFilePayload;
import com.gientech.ragindexservice.application.mq.payload.ReEmbeddingChunkPayload;
import com.gientech.ragindexservice.application.mq.payload.RetryPayload;
import com.gientech.ragindexservice.application.remote.PyMilvusClient;
import com.gientech.ragindexservice.application.remote.request.PyCollection;
import com.gientech.ragindexservice.application.remote.request.PyMilvusInsertRequest;
import com.gientech.ragindexservice.application.remote.request.PyMilvusPageRequest;
import com.gientech.ragindexservice.application.remote.response.PyMilvusResultData;
import com.gientech.ragindexservice.application.service.KnowledgeBaseListAppService;
import com.gientech.ragindexservice.application.service.ReEmbeddingAppService;
import com.gientech.ragindexservice.domain.model.ReEmbeddingFileDO;
import com.gientech.ragindexservice.domain.service.ReEmbeddingFileService;
import com.gientech.ragindexservice.domain.service.ReEmbeddingTaskService;
import com.gientech.ragindexservice.infrastructure.threadpool.runnable.ReEmbeddingChunkRunnable;
import com.google.common.collect.Lists;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.context.config.annotation.RefreshScope;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;

import java.util.List;
import java.util.Objects;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionException;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * @author: shirleychen
 * @date 2025/12/1 16:35
 * @description
 */
@Service
@Slf4j
@RefreshScope
public class ReEmbeddingAppServiceImpl implements ReEmbeddingAppService {

    private final ReEmbeddingTaskService reEmbeddingTaskService;
    private final PyMilvusClient pyMilvusClient;
    private final ThreadPoolExecutor reEmbeddingExecutor;
    private final KnowledgeBaseListAppService knowledgeBaseListAppService;
    private final ReEmbeddingFileService reEmbeddingFileService;

    @Value("${re-embedding.chunk.page-size:50}")
    private Long chunkPageSize;

    private final ObjectMapper objectMapper = new ObjectMapper();

    public ReEmbeddingAppServiceImpl(ReEmbeddingTaskService reEmbeddingTaskService, PyMilvusClient pyMilvusClient, @Qualifier("reEmbeddingExecutor") ThreadPoolExecutor reEmbeddingExecutor, KnowledgeBaseListAppService knowledgeBaseListAppService, ReEmbeddingFileService reEmbeddingFileService) {
        this.reEmbeddingTaskService = reEmbeddingTaskService;
        this.pyMilvusClient = pyMilvusClient;
        this.reEmbeddingExecutor = reEmbeddingExecutor;
        this.knowledgeBaseListAppService = knowledgeBaseListAppService;
        this.reEmbeddingFileService = reEmbeddingFileService;
    }

    @Override
    public void processFile(RetryPayload retryPayload) {
        ProcessFilePayload processFilePayload = (ProcessFilePayload) retryPayload;

        List<CompletableFuture<Void>> chunksReEmbeddingFutures = Lists.newArrayList();
        Long taskId = processFilePayload.getTaskId();
        Long kbId = processFilePayload.getKbId();
        String kbName = processFilePayload.getKbName();
        String collectionName = processFilePayload.getCollectionName();
        KnowledgeBaseFileDTO knowledgeBaseFileDTO = processFilePayload.getFile();
        ModelSimpDTO embeddingModelInfo = processFilePayload.getEmbeddingModelInfo();

        Long fileId = knowledgeBaseFileDTO.getId();
        ReEmbeddingFileDO reEmbeddingFile = reEmbeddingFileService.getReEmbeddingFile(taskId, kbId, fileId, kbName);
        Long taskFileId = reEmbeddingFile.getId();
        clearPreviousChunkData(taskFileId, kbName + "_" + taskId, fileId, taskId);
        processFilePayload.setTaskFileId(taskFileId);
        knowledgeBaseListAppService.updateParseStatusByIds(List.of(fileId), KbFileStatusEnums.RE_EMBEDDING_ING.getValue(), true);
        //1.根据知识库名分页查出所有chunk块

        //TODO 图数据也要重新向量化
        PyMilvusPageRequest pageRequest = new PyMilvusPageRequest();
        List<String> collectionNames = IndexConstant.getCollectionNames(kbName);
        List<String> newCollectionNames = IndexConstant.getNewCollectionNames(kbName + "_" + taskId);
        for (int i = 0; i < collectionNames.size(); i++) {
            String chunkCollectionName = collectionNames.get(i);
            String newChunkCollectionName = newCollectionNames.get(i);
            pageRequest.setCollectionNameList(List.of(chunkCollectionName));
            pageRequest.setPageSize(chunkPageSize);
            pageRequest.setColValues(List.of(String.valueOf(fileId)));
            AtomicBoolean isSetTotal = new AtomicBoolean(false);
            Long pageNo = 1L;
            while (true) {
                //2.分页处理向量化
                pageRequest.setPageNo(pageNo);
                PyMilvusResponse<PyMilvusResultData> response = pyMilvusClient.getDocPage(pageRequest);
                if (Objects.isNull(response) || Objects.isNull(response.getData()) || CollectionUtils.isEmpty(response.getData().getResultData())) {
                    break;
                }
                List<FileChunkDTO> chunks = response.getData().getResultData();
                Long total = response.getData().getTotal();
                if (isSetTotal.compareAndSet(false, true)) {
                    reEmbeddingFileService.addTotalChunkNum(taskFileId, total);
                    Long totalChunkNum = reEmbeddingFileService.lambdaQuery()
                            .select(ReEmbeddingFileDO::getTotalChunkNum)
                            .eq(ReEmbeddingFileDO::getId, taskFileId).one().getTotalChunkNum();
                    if (totalChunkNum.equals(0L)) {
                        reEmbeddingFileService.markStatus(taskFileId, ReEmbeddingTaskEnums.PARSED_SUCCESS);
                        break;
                    }
                    log.info(" currentCollectionName:{}, taskId {} ,set file {} current chunk {}, task totalChunkNum: {}", chunkCollectionName, taskId, fileId, chunks.size(), totalChunkNum);
                }
                CompletableFuture<Void> chunksReEmbeddingFuture = reEmbeddingChunkAsync(taskId, kbName, knowledgeBaseFileDTO, chunks, embeddingModelInfo, newChunkCollectionName, processFilePayload.getKbId(), total, taskFileId);
                chunksReEmbeddingFutures.add(chunksReEmbeddingFuture);
                pageNo++;
            }
        }


        if (!CollectionUtils.isEmpty(chunksReEmbeddingFutures)) {
            CompletableFuture.allOf(
                    chunksReEmbeddingFutures.toArray(new CompletableFuture[0])
            );

            for (int i = 0; i < chunksReEmbeddingFutures.size(); i++) {
                CompletableFuture<Void> f = chunksReEmbeddingFutures.get(i);
                try {
                    f.join();
                } catch (CompletionException ex) {
                    log.error("第 {} 个子任务失败", i, ex.getCause());
                    throw ex;
                }
            }

        }
    }

    private void clearPreviousChunkData(Long taskFileId, String collectionName, Long fileId, Long taskId) {
        reEmbeddingFileService.clearChunkNum(taskFileId);
        List<String> newCollectionNames = IndexConstant.getNewCollectionNames(collectionName);
        newCollectionNames.forEach(newCollectionName -> {
            PyCollection pyCollection = new PyCollection(newCollectionName, fileId);
            PyMilvusResponse<Object> clearResponse = pyMilvusClient.delDocByCol(pyCollection);
            try {
                log.info("taskId:{} processFile {} params {} clearResponse: {}", taskId, fileId, objectMapper.writeValueAsString(pyCollection), objectMapper.writeValueAsString(clearResponse));
            } catch (JsonProcessingException e) {
                log.error(e.getMessage(), e);
            }
        });
    }

    private CompletableFuture<Void> reEmbeddingChunkAsync(Long taskId, String kbName, KnowledgeBaseFileDTO knowledgeBaseFileDTO, List<FileChunkDTO> chunks, ModelSimpDTO embeddingModelInfo, String collectionName, Long kbId, Long currentChunkNum, Long taskFileId) {
        Long fileId = knowledgeBaseFileDTO.getId();
        String fileName = knowledgeBaseFileDTO.getFileName();
        ReEmbeddingChunkPayload reEmbeddingChunkPayload = new ReEmbeddingChunkPayload(knowledgeBaseFileDTO, chunks, embeddingModelInfo, 2, taskId, fileId, collectionName, kbName, kbId, currentChunkNum, taskFileId);
        CompletableFuture<Void> future = new CompletableFuture<>();
        reEmbeddingExecutor.execute(new ReEmbeddingChunkRunnable(this, reEmbeddingChunkPayload, future));
        return future.whenComplete((chunkProcessData, ex) -> {
            if (ex != null) {
                log.error("whenComplete 重新向量化chunk出错...");
                log.error(ex.getMessage(), ex);
                reEmbeddingFileService.addErrorChunkNum(taskFileId, chunks.size());
                Throwable cause = (ex instanceof CompletionException && ex.getCause() != null) ? ex.getCause() : ex;
                throw new CompletionException(cause);
            } else {
                log.info("taskId:{} fileId:{} 处理成功了{}个chunk", taskId, fileId, chunks.size());
                reEmbeddingFileService.addProcessedChunkNum(taskFileId, chunks.size());
            }
            ReEmbeddingFileDO latest = reEmbeddingFileService.lambdaQuery()
                    .select(ReEmbeddingFileDO::getProcessedChunkNum, ReEmbeddingFileDO::getErrorChunkNum)
                    .eq(ReEmbeddingFileDO::getId, taskFileId).one();
            Long processedChunkNum = latest.getProcessedChunkNum();
            Long errorChunkNum = latest.getErrorChunkNum();
            log.info("currentInsertCollectionName:{}, taskFileId:{}, fileId: {} , fileName:{}, 重新向量化成功,当前处理chunk {} 个, 已处理了 {} 个chunk, 处理失败 {} 个chunk", collectionName, taskFileId, fileId, fileName, chunks.size(), processedChunkNum, errorChunkNum);
        });
    }

    @Override
    public void reEmbeddingChunk(RetryPayload reEmbeddingChunkPayload) {
        ReEmbeddingChunkPayload payload = (ReEmbeddingChunkPayload) reEmbeddingChunkPayload;
        List<FileChunkDTO> chunks = payload.getDocumentList();
        //重新向量化
        PyMilvusInsertRequest params = new PyMilvusInsertRequest(payload.getCollectionName(), chunks, payload.getEmbeddingModelInfo());
        try {
            PyMilvusResponse<Object> pyMilvusResponse = pyMilvusClient.insertVectorDocumentsCustom(params);
            log.info("url: /insert_vector_documents_custom, reEmbeddingChunk params: {}, response:{}", (new ObjectMapper()).writeValueAsString(params), (new ObjectMapper()).writeValueAsString(pyMilvusResponse));
            if (!pyMilvusResponse.getCode().equals(200)) {
                log.error("insert vector documents failed with code :{}, msg :{}, params:{}", pyMilvusResponse.getCode(), pyMilvusResponse.getMsg(), JSON.toJSONString(params));
                throw new ApplicationException(ErrCodeEnum.RE_EMBEDDING_ERROR.getErrCode(), (new ObjectMapper()).writeValueAsString(pyMilvusResponse));
            }
        } catch (ApplicationException e) {
            try {
                log.error("insert vector documents failed, params:{}", objectMapper.writeValueAsString(params));
                e.setMessage(String.format("insert vector documents failed, params:%s", objectMapper.writeValueAsString(params)));
            } catch (JsonProcessingException ex) {
                throw e;
            }
            throw e;
        } catch (JsonProcessingException e) {
            log.error("reEmbeddingChunk params json serialize error", e);
        } catch (Exception e) {
            log.error("insert_vector_documents_custom feign error", e);
            throw new RuntimeException(e);
        }
    }
}
