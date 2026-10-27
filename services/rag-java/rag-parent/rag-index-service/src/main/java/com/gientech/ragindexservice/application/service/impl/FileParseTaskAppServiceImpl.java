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
import java.util.concurrent.atomic.AtomicBoolean;
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

    // R14-C-FIX-31c：把 retry-limit 也作为配置暴露出来，只用于启动日志与异常量级告警。
    // 起因：FIX-31b 第一版日志写了 4 个 `{}` 却只给了 3 个参数（retryLimit 当时不存在），
    // slf4j 直接抛 IllegalArgumentException —— 也就是说**"报警器本身坏了，而且坏得很安静"**：
    // 异常被 if 内的 try/catch 吞掉，看起来什么都没发生。补上字段是最小修法。
    @Value("${kb.file-parse.retry-limit:3}")
    private Integer retryLimit;

    /** R14-C-FIX-31d：只在第一次调度时播报一次生效参数（避免每 15 秒刷屏）。 */
    private final AtomicBoolean paramLoggedOnce = new AtomicBoolean(false);

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
        // 说明：FIX-31b 的参数播报**不在**这里做。
        // ① 本类带 @RefreshScope（懒代理），@PostConstruct 不保证启动时执行；
        // ② 更致命的是：占位符与实参个数不匹配时，异常发生在 **appender 格式化阶段**
        //    （StatusConsoleListener），调用点之外的 try/catch 根本兜不住 —— 那条日志会
        //    被整行丢弃且只留下一条框架异常，表现就是"一条都没有"。
        // 所以播报改到 execTask() 首次调度（见 FIX-31d），并且**用字符串拼接**，
        // 从构造上消除"计数对不上"这个失败模式（TL 定的口径：兜底必须构造上不可能失败）。
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
        // R14-C-FIX-31d：把"生效参数"的播报**从 @PostConstruct 挪到第一次调度**。
        // 原因：14:52 那次重启后，主日志里既没有 FIX-31b 的正常播报、也没有它的失败播报，
        // 说明 `@jakarta.annotation.PostConstruct` 这条路径在本服务里没有按预期执行
        // （调度日志 `定时器开始执行文件解析任务` 是有的，说明 bean 已创建并可用）。
        // 与其去猜容器行为，不如把判据挂到**确定会被执行**的路径上：execTask 每 15s 必跑一次。
        if (paramLoggedOnce.compareAndSet(false, true)) {
            int minutes = Objects.isNull(taskTimeout) ? -1 : taskTimeout;
            // 用**字符串拼接**而不是 `{}` 占位符：这条日志已经因为"占位符 4 个、实参 3 个"
            // 崩过两次，且异常发生在 appender 层、调用点的 try/catch 兜不住，整行被静默丢弃。
            // 拼接从构造上就不存在"计数对不上"这个失败模式。
            log.warn("R14-C-FIX-31b 解析任务参数：maxTaskNums=" + maxTaskNums
                    + " taskTimeout=" + minutes + "分钟（折合" + (minutes < 0 ? "?" : (minutes / 60.0)) + "小时）"
                    + "retryLimit=" + retryLimit);
            if (minutes > 24 * 60) {
                log.error("R14-C-FIX-31b kb.file-parse.task-timeout=" + minutes + " 分钟（" + (minutes / 60)
                        + "小时）明显异常，疑似把秒/小时当成了分钟；请核对 application-r12.yml");
            }
        }
        //查询执行中和重试中的任务
        List<FileParseTask> tasks = fileParseTaskDomainService.getTaskByStatus(
                Arrays.asList(ParseTaskStatusEnums.DEAL_ING.getCode(),ParseTaskStatusEnums.RETRY_ING.getCode()));
        //处理任务超时
        doTaskTimeOut(tasks);
        // R14-C-FIX-30（A 更正枚举后定位的自锁）：
        // 真实枚举是 1=PENDING / 2=DEAL_ING / 3=RETRY_ING / 4=SUCCESS / 5=DEAL_FAIL。
        // 原实现把 [2,3] 一起当"正在处理"计数，而待派发队列又是 [1,3] ——
        // 同一个 RETRY_ING(3) 既被算作"在飞"又被当作"可派发"，一旦 3 的条数 >= maxTaskNums，
        // `maxTaskNums > taskNums` 恒假 → 永远不派发新任务（表现为"本次执行 0 个"、文件停在 99）。
        // 修正：**在飞只算 DEAL_ING(2)**；RETRY_ING(3) 属"等待重试"，应可被重新派发。
        long dealIngNums = tasks.stream()
                .filter(t -> ParseTaskStatusEnums.DEAL_ING.getCode().equals(t.getStatus()))
                .count();
        Integer taskNums = (int) dealIngNums;
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
        //R14-C-FIX-32（TL 提的重复派发风险）：派发前必须**原子抢占**。
        //原实现是 `getTaskList` 普通 select 出 1/3 状态的任务，然后同步调解析，
        //**解析成功后才**把 status 置 DEAL_ING、才写 start_time —— 也就是说整个解析窗口内
        //任务状态仍是 PENDING(1)/RETRY_ING(3)，任何第二个执行者（多实例、POST /execTask 手工触发、
        //Redisson 锁 5 秒租约过期后的下一轮）都会把同一 task 再取一次 → 同一文件被两个 worker
        //同时解析（重复写、互相覆盖，且比卡死更难查）。FIX-30 让 RETRY_ING 重新可派发后，
        //这个窗口从"仅 PENDING"扩大到"PENDING + RETRY_ING"。
        //这里用带 status 条件的 UPDATE 做 CAS：只有抢到（受影响行数=1）的执行者才真正派发。
        if (!CollectionUtils.isEmpty(taskList)) {
            List<Integer> claimable = Arrays.asList(
                    ParseTaskStatusEnums.PENDING.getCode(), ParseTaskStatusEnums.RETRY_ING.getCode());
            // 注意：抢占必须**紧贴派发**、逐个做，不能先把整批抢占完再挨个解析。
            // filesParse 是同步调用（一个文件常几十秒到几分钟），若先抢 5 个再串行解析，
            // 后 4 个会长时间处于 DEAL_ING 却不真在跑，既被算作"在飞"、又可能被超时判定误杀。
            for (FileParseTask task : taskList) {
                boolean ok = fileParseTaskDomainService.claimTask(
                        task.getId(), ParseTaskStatusEnums.DEAL_ING.getCode(), claimable);
                if (!ok) {
                    // 已被别的执行者抢走：绝不能重复解析
                    log.warn("R14-C-FIX-32 抢占失败（已被其他执行者取走，跳过重复派发）taskId={}", task.getId());
                    continue;
                }
                // 内存对象同步成"已抢占"状态，filesParse 复用该对象写库时不会退回旧状态
                task.setStatus(ParseTaskStatusEnums.DEAL_ING.getCode());
                task.setStartTime(new Date());
                filesAppParse.filesParse(task);
            }
        }
        return true;
    }

    private void doTaskTimeOut(List<FileParseTask> tasks) {
        if (CollectionUtils.isNotEmpty(tasks)) {
            Iterator<FileParseTask> iterator = tasks.iterator();
            while (iterator.hasNext()){
                FileParseTask task = iterator.next();
                //如果一个小时还是解析中的状态，先重试，如果重试还一定的次数还是失败，直接将状态改为失败
                Date startTime = task.getStartTime();
                // R14-C-FIX-29（A 定位的"调度卡死"）：原实现只在 startTime 非空时才算超时。
                // 说明（A 用 DB 实样更正过）：424..428 的 start_time 其实是**有值**的（13:45:00/01），
                // 当时真正的原因是 `kb.file-parse.task-timeout` 被配成 3600（单位**分钟** = 60 小时），
                // 到期时间是两天半后，所以超时判定不会触发 —— 配置已按 FIX-31 改回 60。
                // 本兜底仍然保留，但定位改为**防御**：start_time 缺失（历史数据/异常中断）时用
                // gmt_modified / gmt_create 作为计时起点，"这条任务多久没被推进过"才是超时的本质。
                if (Objects.isNull(startTime)) {
                    startTime = Objects.nonNull(task.getGmtModified()) ? task.getGmtModified() : task.getGmtCreate();
                    if (Objects.nonNull(startTime)) {
                        log.warn("R14-C-FIX-29 任务 {} 缺 start_time，改用 {} 作为超时计时起点",
                                task.getId(), Objects.nonNull(task.getGmtModified()) ? "gmt_modified" : "gmt_create");
                    }
                }
                Long kbId = task.getKbId();
                boolean timedOut = !Objects.isNull(startTime)
                        && DateUtil.offsetMinute(startTime, taskTimeout).before(new Date());
                // R14-C-FIX-33（A 的建议）：**提前预警**，而不是等到被超时判死才看得见。
                // A 实测 n=316：avg 5.7s、max 189s（3.2 分钟），相对 60 分钟有 ~19 倍余量，
                // 所以 60 暂时安全；但一旦引入大 PDF/OCR/VLM 多图，耗时会跳一个量级。
                // 这里在"已跑过阈值 1/3"时打 warn：既有足够时间处置（调 task-timeout），
                // 又不会因为偶发慢任务刷屏。这行日志出现 = 该评估超时配置了。
                if (!timedOut && Objects.nonNull(startTime) && Objects.nonNull(taskTimeout) && taskTimeout > 0) {
                    long elapsedSec = (System.currentTimeMillis() - startTime.getTime()) / 1000L;
                    long warnSec = taskTimeout * 60L / 3L;
                    if (elapsedSec >= warnSec) {
                        log.warn("R14-C-FIX-33 解析任务 {} 已运行 {}s，超过超时阈值 {}s 的 1/3（taskTimeout={}分钟）fileId={}",
                                task.getId(), elapsedSec, taskTimeout * 60L, taskTimeout, task.getFileId());
                    }
                }
                // R14-C-FIX-30b（A 更正枚举后补充）：RETRY_ING(3) 的任务若重试次数已用尽，
                // 也必须终结为 DEAL_FAIL(5)，否则它会永远停在"重试中"、反复被派发或被计成在飞，
                // 表现就是队列长期不推进。真实枚举：3=RETRY_ING，5=DEAL_FAIL。
                boolean retryExhausted = ParseTaskStatusEnums.RETRY_ING.getCode().equals(task.getStatus())
                        && Objects.nonNull(task.getRetryTimes()) && Objects.nonNull(task.getRetryLimit())
                        && task.getRetryTimes() >= task.getRetryLimit();
                if (timedOut || retryExhausted) {
                    String errorMsg = retryExhausted && !timedOut
                            ? "文件解析重试次数已用尽(retry_times=" + task.getRetryTimes() + "/" + task.getRetryLimit() + ")"
                            : "文件解析超时,文件解析【" + taskTimeout + "分钟】没有响应!";
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

        // R14-C-P2-01（TL 实测定位）：
        // 原实现是"只有当任务当前状态是 RETRY_ING 时才把 retry_times+1"。
        // 但派发前已经做了 CAS 抢占（FIX-32 把状态改成 DEAL_ING），回调时状态**不再是 RETRY_ING**
        // → 这个 +1 永远不执行 → retry_times 恒为 0 → `retryLimit > retryTimes` 恒真 →
        // **永久失败的文件被无限重试**（F 实测 task 471/479 全程 retry_times=0，耗时 1~23 分钟不等）。
        // 计数统一挪到 doFail（真正判定"这次失败"的地方），一次失败算一次，不依赖状态。
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

    /**
     * R14-C-P2-01③：**永久性错误**判定。
     * 这些错误重试 N 次结果必然相同（加密 PDF 不会自己解密、格式不支持不会自愈、文件损坏不会修复），
     * 每次重试都在占一个并发槽、并把"等最终态"的验收拖到超时（实测一条加密 PDF 让整轮 acceptance
     * 从 108 秒涨到 1063 秒）。命中即一次定死为 DEAL_FAIL(5) + 文件 PARSE_FAIL(4)。
     * 关键词保持收敛，宁可漏判（退化成"重试 3 次后失败"）也不要误判（把可恢复错误判死）。
     */
    private boolean isPermanentFailure(String errorMsg) {
        if (Objects.isNull(errorMsg) || errorMsg.isEmpty()) {
            return false;
        }
        String m = errorMsg.toLowerCase();
        String[] keys = {
                "加密", "encrypted", "encrypt", "密码", "password", "口令",
                "不支持", "unsupported", "not supported",
                "损坏", "corrupt", "damaged",
                "格式错误", "invalid format", "无法识别",
                "文件不存在", "not exist", "no such file"
        };
        for (String k : keys) {
            if (m.contains(k)) {
                return true;
            }
        }
        return false;
    }

    private void doFail(String errorMsg, FileParseTask task) {
        Long kbId = task.getKbId();
        Long fileId = task.getFileId();
        Integer retryTimes = task.getRetryTimes();
        Integer retryLimit = task.getRetryLimit();
        task.setErrorMsg(errorMsg);
        Integer parseStatus = KbFileStatusEnums.PARSE_FAIL.getValue();

        // R14-C-P2-01 ①②③（TL/F 实测：同一 task 原地重生、retry_times 恒 0、start_time 被反复刷新）
        // ① 计数在"真正判定失败"的这里 +1，不依赖任务状态（抢占后状态已是 DEAL_ING）。
        int used = (Objects.isNull(retryTimes) ? 0 : retryTimes) + 1;
        task.setRetryTimes(used);
        // ③ 永久性错误白名单：这一类错误重试多少次都必然失败，重试只会占槽 + 拖住"等终态"的验收。
        boolean permanent = isPermanentFailure(errorMsg);
        boolean canRetry = !permanent && Objects.nonNull(retryLimit) && retryLimit > used;
        if (permanent || !canRetry) {
            log.warn("R14-C-P2-01 终结解析任务 task=" + task.getId() + " file=" + fileId
                    + " retryTimes=" + used + "/" + retryLimit
                    + " permanent=" + permanent
                    + (permanent ? "（命中永久失败白名单，不再重试）" : "（重试次数用尽）"));
        }
        if(canRetry){
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
