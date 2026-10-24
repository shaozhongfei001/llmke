package com.gientech.ragindexservice.domain.service.impl;

import com.alibaba.fastjson2.JSONObject;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.gientech.ragcommon.index.enmus.KbFileStatusEnums;
import com.gientech.ragcommon.index.enmus.RetryTaskEnums;
import com.gientech.ragindexservice.application.mq.payload.ProcessFilePayload;
import com.gientech.ragindexservice.application.mq.payload.ReParseFilePayload;
import com.gientech.ragindexservice.application.mq.payload.RetryPayload;
import com.gientech.ragindexservice.application.service.KnowledgeBaseListAppService;
import com.gientech.ragindexservice.application.service.ReEmbeddingAppService;
import com.gientech.ragindexservice.domain.entity.ReEmbeddingRetryTask;
import com.gientech.ragindexservice.domain.mapper.ReEmbeddingRetryTaskMapper;
import com.gientech.ragindexservice.domain.model.ReEmbeddingRetryTaskDO;
import com.gientech.ragindexservice.domain.service.ReEmbeddingFileService;
import com.gientech.ragindexservice.domain.service.ReEmbeddingRetryTaskService;
import com.gientech.ragindexservice.infrastructure.threadpool.runnable.ProcessFileRunnable;
import com.gientech.ragindexservice.infrastructure.threadpool.runnable.ReParseFileRunnable;
import org.codehaus.plexus.util.StringUtils;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.Date;
import java.util.List;
import java.util.Objects;
import java.util.concurrent.CompletableFuture;

/**
 * @author shirleychen
 * @description 针对表【re_embedding_retry_task】的数据库操作Service实现
 * @createDate 2025-11-28 14:35:41
 */
@Service
public class ReEmbeddingRetryTaskServiceImpl extends ServiceImpl<ReEmbeddingRetryTaskMapper, ReEmbeddingRetryTaskDO>
        implements ReEmbeddingRetryTaskService {

    private final ReEmbeddingAppService reEmbeddingAppService;
    private final KnowledgeBaseListAppService knowledgeBaseListAppService;
    private final ReEmbeddingRetryTaskMapper reEmbeddingRetryTaskMapper;
    private final ReEmbeddingFileService reEmbeddingFileService;

    @Value("${re-embedding.max-retry-times:3}")
    private int maxRetryTimes;

    public ReEmbeddingRetryTaskServiceImpl(ReEmbeddingAppService reEmbeddingAppService, KnowledgeBaseListAppService knowledgeBaseListAppService, ReEmbeddingRetryTaskMapper reEmbeddingRetryTaskMapper, ReEmbeddingFileService reEmbeddingFileService) {
        this.reEmbeddingAppService = reEmbeddingAppService;
        this.knowledgeBaseListAppService = knowledgeBaseListAppService;
        this.reEmbeddingRetryTaskMapper = reEmbeddingRetryTaskMapper;
        this.reEmbeddingFileService = reEmbeddingFileService;
    }

    @Override
    @Transactional
    public ReEmbeddingRetryTaskDO saveRetryTask(RetryPayload payload, String lastError, Integer type) {
        //查询是否有文件id，相同且type为FILE的task存在
        int existTaskByFileId = reEmbeddingRetryTaskMapper.findExistTaskByFileId(payload.getFileId(), payload.getTaskId());
        if (existTaskByFileId > 0) {
            return null;
        }
        ReEmbeddingRetryTaskDO taskDO = new ReEmbeddingRetryTaskDO();
        taskDO.setType(type);
        taskDO.setFileId(payload.getFileId());
        taskDO.setTaskId(payload.getTaskId());
        taskDO.setKbId(payload.getKbId());
        taskDO.setRetryTimes(0);
        taskDO.setPayload(getJSON(payload));
        taskDO.setLastError(lastError);
        try {
            this.save(taskDO);
        } catch (DuplicateKeyException e) {
            log.error(e.getMessage());
        } catch (Exception e) {
            log.error(e.getMessage(), e);
        }
        knowledgeBaseListAppService.updateParseStatusByIds(List.of(payload.getFileId()), KbFileStatusEnums.PARSE_FAIL.getValue(), true);
        return taskDO;
    }

    private String getJSON(RetryPayload payload) {
        try {
            return (new ObjectMapper()).writeValueAsString(payload);
        } catch (Exception e) {
            log.error("retry payload get json error", e);
            throw new RuntimeException(e);
        }
    }

    @Override
    @Transactional
    public ReEmbeddingRetryTask getRetryTask() {
        //文件类型优先
        LambdaQueryWrapper<ReEmbeddingRetryTaskDO> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(ReEmbeddingRetryTaskDO::getIsDel, 0);
        //等待处理
        wrapper.eq(ReEmbeddingRetryTaskDO::getStatus, 2);
        wrapper.eq(ReEmbeddingRetryTaskDO::getType, RetryTaskEnums.FILE.getCode());
        wrapper.lt(ReEmbeddingRetryTaskDO::getRetryTimes, maxRetryTimes);
        wrapper.orderByAsc(ReEmbeddingRetryTaskDO::getGmtCreate);
        wrapper.last("LIMIT 1");
        ReEmbeddingRetryTaskDO one = this.getOne(wrapper);
        if (Objects.isNull(one)) {
            //重新解析要等新旧库建好了再解析
            wrapper = new LambdaQueryWrapper<>();
            wrapper.eq(ReEmbeddingRetryTaskDO::getIsDel, 0);
            //等待处理
            wrapper.eq(ReEmbeddingRetryTaskDO::getStatus, 2);
            wrapper.eq(ReEmbeddingRetryTaskDO::getType, RetryTaskEnums.REPARSE.getCode());
            wrapper.lt(ReEmbeddingRetryTaskDO::getRetryTimes, maxRetryTimes);
            wrapper.orderByAsc(ReEmbeddingRetryTaskDO::getGmtCreate);
            wrapper.last("LIMIT 1");
            wrapper.eq(ReEmbeddingRetryTaskDO::getType, RetryTaskEnums.REPARSE.getCode());
            one = this.getOne(wrapper);
            if (Objects.isNull(one)) {
                return null;
            }
        }
        one.setStatus(1);
        //更新状态为处理中
        LambdaUpdateWrapper<ReEmbeddingRetryTaskDO> updateWrapper = new LambdaUpdateWrapper<>();
        updateWrapper.eq(ReEmbeddingRetryTaskDO::getId, one.getId());
        updateWrapper.eq(ReEmbeddingRetryTaskDO::getStatus, 2);
        updateWrapper.set(ReEmbeddingRetryTaskDO::getStatus, 1);
        boolean updated = this.update(updateWrapper);
        if (!updated) {
            // 更新失败说明被其他线程抢先了，返回null
            return null;
        }
        return convertToRetryTask(one);

    }

    private ReEmbeddingRetryTask convertToRetryTask(ReEmbeddingRetryTaskDO taskDO) {
        if (Objects.isNull(taskDO)) {
            return null;
        }
        ReEmbeddingRetryTask reEmbeddingRetryTask = new ReEmbeddingRetryTask();
        reEmbeddingRetryTask.setTaskId(taskDO.getTaskId());
        reEmbeddingRetryTask.setRetryTaskId(taskDO.getId());
        reEmbeddingRetryTask.setRetryTimes(taskDO.getRetryTimes());
        reEmbeddingRetryTask.setGmtCreate(taskDO.getGmtCreate());
        CompletableFuture<Void> future = new CompletableFuture<>();
        RetryPayload retryPayload = JSONObject.parseObject(taskDO.getPayload(), RetryPayload.class);
        reEmbeddingRetryTask.setKbName(retryPayload.getKbName());
        reEmbeddingRetryTask.setCollectionName(retryPayload.getCollectionName());
        reEmbeddingRetryTask.setType(taskDO.getType());
        reEmbeddingRetryTask.setFileId(retryPayload.getFileId());
        if (taskDO.getType().equals(RetryTaskEnums.FILE.getCode())) {
            reEmbeddingRetryTask.setRunnable(new ProcessFileRunnable(reEmbeddingAppService, JSONObject.parseObject(taskDO.getPayload(), ProcessFilePayload.class), future));
        }
        if (taskDO.getType().equals(RetryTaskEnums.REPARSE.getCode())) {
            reEmbeddingRetryTask.setRunnable(new ReParseFileRunnable(knowledgeBaseListAppService, JSONObject.parseObject(taskDO.getPayload(), ReParseFilePayload.class), future, reEmbeddingFileService));
        }
        reEmbeddingRetryTask.setFuture(future);
        return reEmbeddingRetryTask;
    }

    @Override
    public boolean incrRetryTimes(Long retryTaskId) {
        return this.lambdaUpdate().eq(ReEmbeddingRetryTaskDO::getId, retryTaskId).lt(ReEmbeddingRetryTaskDO::getRetryTimes, maxRetryTimes).setSql("retry_times = retry_times + 1").update();
    }

    @Override
    public void updateStatus(Long retryTaskId, Integer status, String lastError) {
        this.lambdaUpdate().eq(ReEmbeddingRetryTaskDO::getId, retryTaskId).set(ReEmbeddingRetryTaskDO::getStatus, status).set(ReEmbeddingRetryTaskDO::getGmtModified, new Date()).set(StringUtils.isNotBlank(lastError), ReEmbeddingRetryTaskDO::getLastError, lastError).update();
    }

    @Override
    public void updateStatus(Long taskId, Long fileId, Integer status, String lastError) {
        this.lambdaUpdate().eq(ReEmbeddingRetryTaskDO::getTaskId, taskId).eq(ReEmbeddingRetryTaskDO::getFileId, fileId).eq(ReEmbeddingRetryTaskDO::getIsDel, 0).set(ReEmbeddingRetryTaskDO::getStatus, status).set(ReEmbeddingRetryTaskDO::getGmtModified, new Date()).set(StringUtils.isNotBlank(lastError), ReEmbeddingRetryTaskDO::getLastError, lastError).update();
    }
}




