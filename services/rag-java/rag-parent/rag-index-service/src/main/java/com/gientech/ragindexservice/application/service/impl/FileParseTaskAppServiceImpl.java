package com.gientech.ragindexservice.application.service.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.date.DateUtil;
import com.alibaba.fastjson2.JSONObject;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.plugins.pagination.PageDTO;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.index.enmus.*;
import com.gientech.ragcommon.index.parameter.FileParseTaskInfo;
import com.gientech.ragcommon.index.request.TaskReq;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.ragindexservice.application.service.FileAppService;
import com.gientech.ragindexservice.application.service.FileParseTaskAppService;
import com.gientech.ragindexservice.domain.entity.FileParseTask;
import com.gientech.ragindexservice.domain.entity.KnowledgeBaseList;
import com.gientech.ragindexservice.domain.service.FileParseTaskDomainService;
import com.gientech.ragindexservice.domain.service.KnowledgeBaseListDomainService;
import com.gientech.ragindexservice.domain.service.SynLogDomainService;
import com.gientech.ragcommon.index.dto.FileParseTaskDTO;
import com.gientech.ragcommon.index.request.SaveFileParseTaskReq;
import com.gientech.ragcommon.index.request.UpdateFileParseTaskReq;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.collections4.CollectionUtils;
import org.assertj.core.util.Lists;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.context.config.annotation.RefreshScope;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.stream.Collectors;

@RefreshScope
@Slf4j
@Service
public class FileParseTaskAppServiceImpl implements FileParseTaskAppService {

    @Autowired
    private FileParseTaskDomainService fileParseTaskDomainService;

    @Autowired
    private FileAppService filesAppParse;

    @Autowired
    private KnowledgeBaseListDomainService knowledgeBaseListDomainService;

    @Autowired
    private SynLogDomainService synLogDomainService;

    @Value("${kb.file-parse.task-nums}")
    private Integer maxTaskNums;

    @Value("${kb.file-parse.task-timeout}")
    private Integer taskTimeout;

    @Override
    public FileParseTaskDTO findById(Long id) {
        if (Objects.isNull(id))
            return null;
        FileParseTask byId = fileParseTaskDomainService.findById(id);
        return BeanUtil.copyProperties(byId, FileParseTaskDTO.class);
    }

    @Override
    public Boolean save(SaveFileParseTaskReq fileParseTaskReq) {
        if (Objects.isNull(fileParseTaskReq))
            return false;
        return fileParseTaskDomainService.save(BeanUtil.copyProperties(fileParseTaskReq, FileParseTask.class));
    }

    @Override
    public Boolean updateById(UpdateFileParseTaskReq fileParseTaskReq) {
        if (Objects.isNull(fileParseTaskReq))
            return false;
        return fileParseTaskDomainService.updateById(BeanUtil.copyProperties(fileParseTaskReq, FileParseTask.class));
    }

    @Override
    public Page<FileParseTaskDTO> list(Long pageNo, Long pageSize) {
        pageNo = Objects.isNull(pageNo) ? 1 : pageNo;
        pageSize = Objects.isNull(pageSize) ? 10 : pageSize;
        Page<FileParseTask> page = fileParseTaskDomainService.list(pageNo, pageSize);
        Page<FileParseTaskDTO> result = new PageDTO<>();
        BeanUtil.copyProperties(page, result);
        result.setRecords(BeanUtil.copyToList(page.getRecords(), FileParseTaskDTO.class));
        return result;
    }

    @Override
    public Boolean deleteById(Long id) {
        if (Objects.isNull(id))
            return false;
        return fileParseTaskDomainService.deleteById(id);
    }

    /**
     * R13-RUN-05：进程重启后，上一轮"处理中(2)"的任务永远不会再有人推进，
     * 而调度器按 DB 中 DEAL_ING/RETRY_ING 数量限流，会导致**队列永久卡死**
     * （表现为上传后一直排队、状态停在 98/99）。
     * 启动时把残留的处理中/重试中任务打回待处理，保证重启可自愈（任务本身幂等）。
     */
    @jakarta.annotation.PostConstruct
    public void recoverStaleTasksOnStartup() {
        try {
            List<FileParseTask> stale = fileParseTaskDomainService.getTaskByStatus(
                    Arrays.asList(ParseTaskStatusEnums.DEAL_ING.getCode(), ParseTaskStatusEnums.RETRY_ING.getCode()));
            if (CollectionUtils.isEmpty(stale)) {
                return;
            }
            for (FileParseTask t : stale) {
                UpdateFileParseTaskReq req = new UpdateFileParseTaskReq();
                req.setId(t.getId());
                req.setStatus(ParseTaskStatusEnums.PENDING.getCode());
                fileParseTaskDomainService.updateById(BeanUtil.copyProperties(req, FileParseTask.class));
            }
            log.warn("recovered {} stale parse tasks on startup", stale.size());
        } catch (Exception ex) {
            log.error("recover stale parse tasks failed: {}", ex.getMessage());
        }
    }

    @Override
    public Boolean execTask() {
        //查询执行中和重试中的任务
        List<FileParseTask> tasks = fileParseTaskDomainService.getTaskByStatus(
                Arrays.asList(ParseTaskStatusEnums.DEAL_ING.getCode(),ParseTaskStatusEnums.RETRY_ING.getCode()));
        //处理任务超时
        doTaskTimeOut(tasks);
        Integer taskNums = tasks.size();
        //获取需要执行的任务数据(待处理 重试中)
        List<FileParseTask> taskList = Lists.newArrayList();
        if (maxTaskNums > taskNums)
            taskList = fileParseTaskDomainService.getTaskList(
                    Arrays.asList(ParseTaskStatusEnums.PENDING.getCode(), ParseTaskStatusEnums.RETRY_ING.getCode()),
                    (maxTaskNums - taskNums));

        log.info("允许执行的任务数:{},正在处理的任务数:{},正在执行的任务id:{},本次执行的任务数:{},本次执行的任务id:{}",
                maxTaskNums,
                taskNums, JSONObject.toJSONString(tasks.stream().map(FileParseTask::getId).collect(Collectors.toList())),
                taskList.size(), JSONObject.toJSONString(taskList.stream().map(FileParseTask::getId).collect(Collectors.toList())));

        //调用解析服务
        if (!CollectionUtils.isEmpty(taskList))
            taskList.forEach(task -> filesAppParse.filesParse(task));
        return true;
    }

    private void doTaskTimeOut(List<FileParseTask> tasks) {
        if (CollectionUtils.isNotEmpty(tasks)) {
            Iterator<FileParseTask> iterator = tasks.iterator();
            while (iterator.hasNext()){
                FileParseTask task = iterator.next();
                //如果一个小时还是解析中的状态，先重试，如果重试还一定的次数还是失败，直接将状态改为失败
                Date startTime = task.getStartTime();
                Long kbId = task.getKbId();
                if(!Objects.isNull(startTime) && DateUtil.offsetMinute(startTime, taskTimeout).before(new Date())){
                    String errorMsg = "文件解析超时,文件解析【"+taskTimeout+"分钟】没有响应!";
                    Long fileId = task.getFileId();
                    task.setStatus(ParseTaskStatusEnums.DEAL_FAIL.getCode());
                    task.setErrorMsg(errorMsg);
                    task.setRetryTimes(task.getRetryLimit());
                    task.setEndTime(new Date());
                    //更新文件为解析失败的状态
                    knowledgeBaseListDomainService.updateParseStatusByIds(Arrays.asList(fileId), KbFileStatusEnums.PARSE_FAIL.getValue(),true);
                    //更新任务为解析失败
                    fileParseTaskDomainService.updateById(task);
                    //记录异常日志
                    synLogDomainService.saveLog(kbId, fileId, LogTypeEnums.FILE_PARSE.getCode(), null, errorMsg);
                    iterator.remove();
                }
            }
        }
    }

    @Override
    public Boolean taskCallback(TaskReq taskReq) {
        log.info("解析任务回调请求参数:{}", JSONObject.toJSONString(taskReq));
        Boolean success = taskReq.getSuccess();
        Long taskId = taskReq.getTaskId();
        List<TaskReq.TaskStatus> taskStatuses = taskReq.getTaskStatuses();
        FileParseTask task = fileParseTaskDomainService.findById(taskId);
        Integer retryTimes = task.getRetryTimes();

        //如果是重试中的状态，重试次数加1
        if(ParseTaskStatusEnums.RETRY_ING.getCode().equals(task.getStatus()))
            task.setRetryTimes(retryTimes + 1);

        if(success){
            //一次解析一个文件
            TaskReq.TaskStatus taskStatus = taskStatuses.get(0);
            doSuccess(task, taskStatus);
        }else {
            doFail(JSONObject.toJSONString(taskReq), task);
        }
        return true;
    }

    private void doSuccess(FileParseTask task, TaskReq.TaskStatus taskStatus) {
        String taskInfo = task.getTaskInfo();
        FileParseTaskInfo fileParseTaskInfo = JSONObject.parseObject(taskInfo, FileParseTaskInfo.class);
        Boolean isExtract = fileParseTaskInfo.getIsExtract();
        Boolean isGraphParse = fileParseTaskInfo.getIsGraphParse();
        boolean needChunk = fileParseTaskInfo.isNeedChunk();

        //设置用户上下文信息
        setUserContext(fileParseTaskInfo.getUserId(),fileParseTaskInfo.getUserName());

        Long fileId = task.getFileId();
        task.setStatus(ParseTaskStatusEnums.SUCESS.getCode());
        task.setEndTime(new Date());
        //更新解析任务状态
        fileParseTaskDomainService.updateById(task);

        //更新文件相关信息
        KnowledgeBaseList knowledgeBaseFile = new KnowledgeBaseList();
        knowledgeBaseFile.setId(fileId);
        knowledgeBaseFile.setGmtModified(new Date());
        if (needChunk) {
            //修订时间
            String reviseData = taskStatus.getReviseDate();
            knowledgeBaseFile.setReviseDate(reviseData);
            knowledgeBaseFile.setChunking(needChunk);
        }
        knowledgeBaseFile.setStatus(KbFileStatusEnums.PARSE_SUCCESS.getValue());
        knowledgeBaseFile.setChunkType(fileParseTaskInfo.getFileType());
        knowledgeBaseListDomainService.update(knowledgeBaseFile);

        //文件多版本解析(仅文件解析)
        Integer parseType = fileParseTaskInfo.getParseType();
        if (!isExtract && (ParseTypeEnums.FILE_PARSE.getCode().equals(parseType) || ParseTypeEnums.FAQ_FILE_PARSE.getCode().equals(parseType)))
            filesAppParse.fileMultiversionParse(
                    fileParseTaskInfo.getKnowledgeBaseId(),
                    fileParseTaskInfo.getFiles().stream().map(FileParseTaskInfo.File::getFileId).collect(Collectors.toList()),
                    MultiversionParseEnums.FILENAME_CONTENT,
                    Arrays.asList(ParseTypeEnums.FILE_PARSE.getCode(), ParseTypeEnums.FAQ_FILE_PARSE.getCode()));

        //处理FAQ抽取
        if (isExtract)
            filesAppParse.faqExtract(fileParseTaskInfo);

        //文件图谱抽取
        if(isGraphParse)
            filesAppParse.generateGraph(fileParseTaskInfo);
    }

    private void setUserContext(String userId, String userName) {
        User user = new User();
        user.setUserId(userId);
        user.setUserName(userName);
        UserContext.setUser(user);
    }

    private void doFail(String errorMsg, FileParseTask task) {
        Long kbId = task.getKbId();
        Long fileId = task.getFileId();
        Integer retryTimes = task.getRetryTimes();
        Integer retryLimit = task.getRetryLimit();
        task.setErrorMsg(errorMsg);
        Integer parseStatus = KbFileStatusEnums.PARSE_FAIL.getValue();
        if(retryLimit > retryTimes){
            task.setStatus(ParseTaskStatusEnums.RETRY_ING.getCode());
            parseStatus = KbFileStatusEnums.RETRY.getValue();
        }else {
            task.setStatus(ParseTaskStatusEnums.DEAL_FAIL.getCode());
            FileParseTaskInfo fileParseTaskInfo = JSONObject.parseObject(task.getTaskInfo(), FileParseTaskInfo.class);
            Boolean isExtract = fileParseTaskInfo.getIsExtract();
            Boolean isGraphParse = fileParseTaskInfo.getIsGraphParse();
            if(isExtract)
                knowledgeBaseListDomainService.updateExtractStatusByIds(List.of(fileId), FaqExtractStatusEnums.EXTRACT_FAIL.getValue());
            if(isGraphParse)
                knowledgeBaseListDomainService.updateExtractStatusByIds(List.of(fileId), GraphParseStatusEnums.PARSE_FAIL.getValue());
        }
        //更新文件解析状态
        knowledgeBaseListDomainService.updateParseStatusByIds(List.of(fileId), parseStatus, true);
        //记录异常日志
        synLogDomainService.saveLog(kbId, fileId, LogTypeEnums.FILE_PARSE.getCode(), null, errorMsg);
        //更新解析任务状态
        fileParseTaskDomainService.updateById(task);
    }


    @Override
    public Long getSequenceByFileId(Long fileId) {
        if (Objects.isNull(fileId) || fileId < 0) {
            throw new ApplicationException(ErrCodeEnum.DOC_ID_PARAM_ERROR);
        }
        return fileParseTaskDomainService.getSequenceByFileId(fileId);
    }
}
