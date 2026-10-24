package com.gientech.ragindexservice.application.mq;

import com.alibaba.fastjson.JSON;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.auth.dto.UserInfoDTO;
import com.gientech.ragcommon.index.constant.IndexConstant;
import com.gientech.ragcommon.index.dto.KnowledgeBaseFileDTO;
import com.gientech.ragcommon.index.dto.ModelSimpDTO;
import com.gientech.ragcommon.index.enmus.KbFileStatusEnums;
import com.gientech.ragcommon.index.enmus.ReEmbeddingTaskEnums;
import com.gientech.ragcommon.index.enmus.RetryTaskEnums;
import com.gientech.ragcommon.index.request.KnowledgeBaseFileQueryReq;
import com.gientech.ragcommon.index.response.PyMilvusResponse;
import com.gientech.ragcommon.infrastructure.emuns.MessageChannel;
import com.gientech.ragindexservice.application.mq.message.ReEmbeddingTaskInfo;
import com.gientech.ragindexservice.application.mq.payload.ProcessFilePayload;
import com.gientech.ragindexservice.application.mq.payload.ReParseFilePayload;
import com.gientech.ragindexservice.application.remote.PyMilvusClient;
import com.gientech.ragindexservice.application.remote.UserClient;
import com.gientech.ragindexservice.application.remote.request.PyCollection;
import com.gientech.ragindexservice.application.service.KnowledgeBaseListAppService;
import com.gientech.ragindexservice.application.service.ReEmbeddingAppService;
import com.gientech.ragindexservice.domain.model.ReEmbeddingFileDO;
import com.gientech.ragindexservice.domain.model.ReEmbeddingTaskDO;
import com.gientech.ragindexservice.domain.service.ReEmbeddingFileService;
import com.gientech.ragindexservice.domain.service.ReEmbeddingRetryTaskService;
import com.gientech.ragindexservice.domain.service.ReEmbeddingTaskService;
import com.gientech.ragindexservice.infrastructure.threadpool.runnable.ProcessFileRunnable;
import com.gientech.ragindexservice.infrastructure.threadpool.runnable.ReParseFileRunnable;
import com.google.common.collect.Lists;
import lombok.extern.slf4j.Slf4j;
import org.apache.rocketmq.spring.annotation.MessageModel;
import org.apache.rocketmq.spring.annotation.RocketMQMessageListener;
import org.apache.rocketmq.spring.core.RocketMQListener;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.util.CollectionUtils;

import java.time.LocalDateTime;
import java.util.Collections;
import java.util.List;
import java.util.Objects;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionException;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 *
 */
@Slf4j
@Component
@RocketMQMessageListener(consumerGroup = MessageChannel.RE_EMBEDDING_GROUP,
        topic = MessageChannel.RE_EMBEDDING_TOPIC, messageModel = MessageModel.CLUSTERING
)
public class ReEmbeddingConsume implements RocketMQListener<ReEmbeddingTaskInfo> {

    private final PyMilvusClient pyMilvusClient;
    private final ReEmbeddingRetryTaskService reEmbeddingRetryTaskService;
    private final UserClient userClient;
    private final ReEmbeddingFileService reEmbeddingFileService;
    @Value("${re-embedding.file.page-size:50}")
    private Long filePageSize;


    private final KnowledgeBaseListAppService knowledgeBaseListAppService;

    private final ThreadPoolExecutor fileProcessExecutor;

    private final ReEmbeddingTaskService reEmbeddingTaskService;
    private final ReEmbeddingAppService reEmbeddingAppService;
    private static final Long FIRST_PAGE = 1L;

    public ReEmbeddingConsume(KnowledgeBaseListAppService knowledgeBaseListAppService, @Qualifier("fileProcessExecutor") ThreadPoolExecutor fileProcessExecutor, ReEmbeddingTaskService reEmbeddingTaskService, ReEmbeddingAppService reEmbeddingAppService, PyMilvusClient pyMilvusClient, ReEmbeddingRetryTaskService reEmbeddingRetryTaskService, UserClient userClient, ReEmbeddingFileService reEmbeddingFileService) {
        this.knowledgeBaseListAppService = knowledgeBaseListAppService;
        this.fileProcessExecutor = fileProcessExecutor;
        this.reEmbeddingTaskService = reEmbeddingTaskService;
        this.reEmbeddingAppService = reEmbeddingAppService;
        this.pyMilvusClient = pyMilvusClient;
        this.reEmbeddingRetryTaskService = reEmbeddingRetryTaskService;
        this.userClient = userClient;
        this.reEmbeddingFileService = reEmbeddingFileService;
    }

    @Override
    public void onMessage(ReEmbeddingTaskInfo reEmbeddingTaskInfo) {
        Long taskId = reEmbeddingTaskInfo.getId();
        ReEmbeddingTaskDO task = reEmbeddingTaskService.getById(taskId);
        if (Objects.isNull(task) || !ReEmbeddingTaskEnums.WAIT_TO_START.getCode().equals(task.getStatus())) {
            return;
        }
        Long kbId = reEmbeddingTaskInfo.getKbId();
        ModelSimpDTO embeddingModelInfo = reEmbeddingTaskInfo.getEmbeddingModelInfo();

        String kbName = reEmbeddingTaskInfo.getKnowledgeBaseName();
        List<CompletableFuture<Void>> fileFutures = Lists.newArrayList();
        //更新task解析状态为解析中
        reEmbeddingTaskService.updateStatus(taskId, ReEmbeddingTaskEnums.PARSING);

        KnowledgeBaseFileQueryReq req = new KnowledgeBaseFileQueryReq();
        req.setKbIds(Collections.singleton(kbId));
        req.setPageSize(filePageSize);
        req.setPageNo(FIRST_PAGE);
        req.setStatusArray(new int[]{KbFileStatusEnums.PARSE_ING.getValue(), KbFileStatusEnums.PARSE_WAIT.getValue(), KbFileStatusEnums.PARSE_FAIL.getValue(), KbFileStatusEnums.RE_EMBEDDING_ING.getValue()});
        List<KnowledgeBaseFileDTO> parsingAndWaitFiles = knowledgeBaseListAppService.onlyFileListByTime(req);
        //1.创建新的milvus collection
        String collectionName = reEmbeddingTaskInfo.getNewMilvusCollectionName();


        req.setStartTime(LocalDateTime.now());
        req.setStatusArray(new int[]{KbFileStatusEnums.PARSE_SUCCESS.getValue()});
        List<Long> parsedFileIds = Lists.newArrayList();
        List<String> newCollectionNames = IndexConstant.getNewCollectionNames(collectionName);
        while (true) {
            //2.根据知识库名分页查出所有文件
            AtomicBoolean isSetTotal = new AtomicBoolean(false);
            Page<KnowledgeBaseFileDTO> knowledgeBaseFileDTOPage = knowledgeBaseListAppService.flatFiles(req);
            if (knowledgeBaseFileDTOPage.getRecords().isEmpty()) {
                if (req.getPageNo().equals(FIRST_PAGE)) {
                    //说明知识库是空的
                    reEmbeddingTaskService.updateStatus(taskId, ReEmbeddingTaskEnums.PARSED_SUCCESS);
                }
                break;
            }
            if (isSetTotal.compareAndSet(false, true)) {
                reEmbeddingTaskService.addTotalFileNum(taskId, knowledgeBaseFileDTOPage.getTotal());
                Long totalFileNum = reEmbeddingTaskService.lambdaQuery().select(ReEmbeddingTaskDO::getTotalFileNum).eq(ReEmbeddingTaskDO::getId, taskId).one().getTotalFileNum();
                log.info("kb {} total files: {}, currentPageFiles: {}", kbId, totalFileNum, knowledgeBaseFileDTOPage.getRecords().size());
                //仅执行一次
                newCollectionNames.forEach(newCollectionName -> {
                    PyMilvusResponse<Object> createMilvusResponse = pyMilvusClient.createMilvusCollection(new PyCollection(newCollectionName, embeddingModelInfo));
                    log.info("createMilvusCollection: collectionName={}, response:{}", newCollectionName, createMilvusResponse);
                });
            }

            List<KnowledgeBaseFileDTO> files = knowledgeBaseFileDTOPage.getRecords();
            List<Long> fileIds = files.stream().map(KnowledgeBaseFileDTO::getId).toList();
            parsedFileIds.addAll(fileIds);
            knowledgeBaseListAppService.updateParseStatusByIds(fileIds, KbFileStatusEnums.RE_EMBEDDING_ING.getValue(), true);
            //异步处理分页文件列表
            List<CompletableFuture<Void>> fileFuture = files.stream().map(file -> processFileAsync(taskId, kbName, file, reEmbeddingTaskInfo.getEmbeddingModelInfo(), collectionName)).toList();
            log.debug("dealing page {} of {}, {}, files are {}", req.getPageNo(), knowledgeBaseFileDTOPage.getPages(), kbName, JSON.toJSONString(files.stream().map(KnowledgeBaseFileDTO::getFileName).toList()));
            fileFutures.addAll(fileFuture);
            req.setPageNo(req.getPageNo() + 1);
        }

        if (!CollectionUtils.isEmpty(fileFutures)) {
            //等待所有文件处理完成
            CompletableFuture.allOf(fileFutures.toArray(new CompletableFuture[0])).join();
            //判断所有文件是否都是正常执行
            int nonProcessedFileCount = reEmbeddingFileService.getNonProcessedFileCount(taskId, kbId);
            log.info("nonProcessedFileCount: {}, 为0可以开始迁移", nonProcessedFileCount);
            if (nonProcessedFileCount == 0) {
                reEmbeddingTaskService.updateStatus(taskId, ReEmbeddingTaskEnums.PARSED_SUCCESS);
                //删除旧库
                try {
                    reEmbeddingTaskService.doMigrate(fileProcessExecutor, kbName, collectionName, embeddingModelInfo, kbId, taskId, null);
                } catch (Exception e) {
                    log.error("删除旧库出错", e);
                }
            }
        }
        log.info("所有文件处理完成,开始处理解析中、排队中和刚上传的文件...");
        //获取kbFiles 发送重新解析
        doReParseFiles(req, parsingAndWaitFiles, taskId, reEmbeddingTaskInfo.getEmbeddingModelInfo(), kbName, kbId, task.getCreateBy());
    }

    private CompletableFuture<Void> processFileAsync(Long taskId, String kbName, KnowledgeBaseFileDTO file, ModelSimpDTO embeddingModelInfo, String collectionName) {
        ProcessFilePayload processFilePayload = new ProcessFilePayload(file, embeddingModelInfo, RetryTaskEnums.FILE.getCode(), taskId, file.getId(), collectionName, kbName, file.getKbId(), null);
        CompletableFuture<Void> future = new CompletableFuture<>();
        fileProcessExecutor.execute(new ProcessFileRunnable(reEmbeddingAppService, processFilePayload, future));
        return future.handle((v, ex) -> {
            if (ex != null) {
                Throwable cause = (ex instanceof CompletionException && ex.getCause() != null) ? ex.getCause() : ex;
                log.error("processFileAsync error...", cause);
                knowledgeBaseListAppService.updateParseStatusByIds(
                        List.of(file.getId()), KbFileStatusEnums.PARSE_FAIL.getValue(), true
                );
                log.info("fileId:{}, kbName:{} set status parsed fail", file.getId(), kbName);
                reEmbeddingTaskService.updateStatus(taskId, ReEmbeddingTaskEnums.PARSED_FAIL);
                reEmbeddingFileService.markStatus(processFilePayload.getTaskFileId(), ReEmbeddingTaskEnums.PARSED_FAIL);
                if (!processFilePayload.isRetry()) {
                    reEmbeddingTaskService.markErrorFile(taskId, 1);
                }
                processFilePayload.setRetry(true);
                reEmbeddingRetryTaskService.saveRetryTask(processFilePayload, cause.getMessage(), RetryTaskEnums.FILE.getCode());
                // 如果你希望 fileFuture 在失败时也体现失败，就继续抛出
//                throw new CompletionException(cause);
            }

            if (!processFilePayload.isRetry()) {
                reEmbeddingTaskService.markProcessedFile(taskId, 1);
            }
            reEmbeddingFileService.markStatus(processFilePayload.getTaskFileId(), ReEmbeddingTaskEnums.PARSED_SUCCESS);
            log.info("fileId:{}, fileName:{}, kbName:{} 重新向量化成功", file.getId(), file.getFileName(), kbName);
            return null;
        });
    }

    private void doReParseFiles(KnowledgeBaseFileQueryReq req, List<KnowledgeBaseFileDTO> parsingAndWaitFiles, Long taskId, ModelSimpDTO embeddingModelInfo, String kbName, Long kbId, String userName) {
        req.setEndTime(LocalDateTime.now());
        req.setStatusArray(new int[]{KbFileStatusEnums.PARSE_SUCCESS.getValue(), KbFileStatusEnums.PARSE_WAIT.getValue(), KbFileStatusEnums.PARSE_ING.getValue(), KbFileStatusEnums.PARSE_FAIL.getValue(), KbFileStatusEnums.RE_EMBEDDING_ING.getValue()});
        List<KnowledgeBaseFileDTO> files = knowledgeBaseListAppService.onlyFileListByTime(req);
        files.addAll(parsingAndWaitFiles);
        UserInfoDTO userInfoDTO = userClient.getUserInfoByUserName(userName);
        if (CollectionUtils.isEmpty(files)) {
            return;
        }
        log.info("reParseFile 需要重新解析 {} 个文件", files.size());

        CompletableFuture<Void> future = new CompletableFuture<>();
        reEmbeddingTaskService.addTotalFileNum(taskId, (long) files.size());
        List<CompletableFuture<Void>> reParseFileFutures = Lists.newArrayList();
        files.forEach(file -> {
            ReEmbeddingFileDO reEmbeddingFile = reEmbeddingFileService.getReEmbeddingFile(taskId, kbId, file.getId(), kbName);
            Long taskFileId = reEmbeddingFile.getId();
            ReParseFilePayload reParseFilePayload = new ReParseFilePayload(taskId, 3, embeddingModelInfo, file.getId(), kbName, kbName, kbId, file, userInfoDTO, taskFileId);
            fileProcessExecutor.execute(new ReParseFileRunnable(knowledgeBaseListAppService, reParseFilePayload, future, reEmbeddingFileService));
            CompletableFuture<Void> reParseFuture = future.whenComplete((v, ex) -> {
                if (ex != null) {
                    log.error("whenComplete error reParseFile", ex);
                    reEmbeddingTaskService.updateStatus(taskId, ReEmbeddingTaskEnums.PARSED_FAIL);
                    reEmbeddingFileService.markStatus(reParseFilePayload.getTaskFileId(), ReEmbeddingTaskEnums.PARSED_FAIL);
                    if (!reParseFilePayload.isRetry()) {
                        reEmbeddingTaskService.markErrorFile(taskId, 1);
                    }
                } else {
                    reEmbeddingFileService.markStatus(reParseFilePayload.getTaskFileId(), ReEmbeddingTaskEnums.PROCESSED);
                    if (!reParseFilePayload.isRetry()) {
                        reEmbeddingTaskService.markProcessedFile(taskId, 1);
                    }
                }
            }).exceptionally(e -> {
                log.error("exceptionally reParseFile error", e);
                reEmbeddingTaskService.updateStatus(taskId, ReEmbeddingTaskEnums.PARSED_FAIL);
                return null;
            });
            reParseFileFutures.add(reParseFuture);
        });

        //避免主线程执行完成之后没有执行到whenComplete
        if (!CollectionUtils.isEmpty(reParseFileFutures)) {
            CompletableFuture.allOf(reParseFileFutures.toArray(new CompletableFuture[0])).join();
        }
    }

}
