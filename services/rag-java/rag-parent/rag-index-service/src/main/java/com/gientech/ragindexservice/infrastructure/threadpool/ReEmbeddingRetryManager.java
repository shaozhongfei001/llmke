package com.gientech.ragindexservice.infrastructure.threadpool;

import com.alibaba.fastjson2.JSONObject;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.index.constant.IndexConstant;
import com.gientech.ragcommon.index.enmus.KbFileStatusEnums;
import com.gientech.ragcommon.index.enmus.ReEmbeddingRetryEnums;
import com.gientech.ragcommon.index.enmus.ReEmbeddingTaskEnums;
import com.gientech.ragcommon.index.enmus.RetryTaskEnums;
import com.gientech.ragcommon.index.response.PyEsResponse;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.ragindexservice.application.mq.payload.ProcessFilePayload;
import com.gientech.ragindexservice.application.mq.payload.RetryPayload;
import com.gientech.ragindexservice.application.remote.PyEsClient;
import com.gientech.ragindexservice.application.remote.PyMilvusClient;
import com.gientech.ragindexservice.application.remote.request.PyCollection;
import com.gientech.ragindexservice.application.remote.request.PyEsIndex;
import com.gientech.ragindexservice.application.service.KnowledgeBaseListAppService;
import com.gientech.ragindexservice.domain.entity.ReEmbeddingRetryTask;
import com.gientech.ragindexservice.domain.model.ReEmbeddingRetryTaskDO;
import com.gientech.ragindexservice.domain.service.ReEmbeddingFileService;
import com.gientech.ragindexservice.domain.service.ReEmbeddingRetryTaskService;
import com.gientech.ragindexservice.domain.service.ReEmbeddingTaskService;
import com.google.common.util.concurrent.ThreadFactoryBuilder;
import lombok.extern.slf4j.Slf4j;
import org.redisson.api.RLock;
import org.redisson.api.RedissonClient;
import org.springframework.beans.factory.DisposableBean;
import org.springframework.beans.factory.InitializingBean;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.context.config.annotation.RefreshScope;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Objects;
import java.util.concurrent.*;

/**
 * @author: shirleychen
 * @date 2025/12/2 10:15
 * @description
 */
@Component
@Slf4j
@RefreshScope
public class ReEmbeddingRetryManager implements InitializingBean, DisposableBean {

    private final PyEsClient pyEsClient;
    private final PyMilvusClient pyMilvusClient;
    private final ReEmbeddingTaskService reEmbeddingTaskService;
    private final ThreadPoolExecutor fileProcessExecutor;
    private final ReEmbeddingFileService reEmbeddingFileService;
    private Semaphore semaphore;
    private ExecutorService workerPool;
    private ExecutorService taskExecutor;
    private final static int maxLength = 65535;

    private volatile boolean running = true;

    @Value("${retry.max-concurrent:32}")
    private int maxConcurrent;

    @Value("${retry.worker-threads:32}")
    private int workerThreads;

    @Value("${retry.max-retries:3}")
    private int maxRetries;

    @Value("${retry.timeout:10}")
    private int timeoutMinutes;

    private static final String RETRY_TASK_LOCK_KEY_PREFIX = "reEmbeddingRetryTask:lock:";
    private static final String MIGRATE_LOCK_KEY_PREFIX = "reEmbeddingMigrate:lock:";

    private final ReEmbeddingRetryTaskService reEmbeddingRetryTaskService;
    private final RedissonClient redissonClient;
    private final KnowledgeBaseListAppService knowledgeBaseListAppService;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public ReEmbeddingRetryManager(ReEmbeddingRetryTaskService reEmbeddingRetryTaskService, PyEsClient pyEsClient, PyMilvusClient pyMilvusClient, KnowledgeBaseListAppService knowledgeBaseListAppService, ReEmbeddingTaskService reEmbeddingTaskService, @Qualifier("fileProcessExecutor") ThreadPoolExecutor fileProcessExecutor, ReEmbeddingFileService reEmbeddingFileService, RedissonClient redissonClient) {
        this.reEmbeddingRetryTaskService = reEmbeddingRetryTaskService;
        this.redissonClient = redissonClient;
        this.pyEsClient = pyEsClient;
        this.pyMilvusClient = pyMilvusClient;
        this.knowledgeBaseListAppService = knowledgeBaseListAppService;
        this.reEmbeddingTaskService = reEmbeddingTaskService;
        this.fileProcessExecutor = fileProcessExecutor;
        this.reEmbeddingFileService = reEmbeddingFileService;
    }

    private String buildLockKey(Long retryTaskId) {
        return RETRY_TASK_LOCK_KEY_PREFIX + retryTaskId;
    }

    private String buildMigrateLockKey(Long taskId) {
        return MIGRATE_LOCK_KEY_PREFIX + taskId;
    }

    /**
     * Spring容器初始化完成后自动启动
     */
    @Override
    public void afterPropertiesSet() throws Exception {
        log.info("========================================");
        log.info("初始化自动重试Worker线程池");
        log.info("maxConcurrent: {}", maxConcurrent);
        log.info("workerThreads: {}", workerThreads);
        log.info("maxRetries: {}", maxRetries);
        log.info("========================================");

        this.semaphore = new Semaphore(maxConcurrent);

        // Worker线程池：专门等待和取任务
        this.workerPool = new ThreadPoolExecutor(
                workerThreads,
                workerThreads,
                1L, TimeUnit.MINUTES,
                new SynchronousQueue<>(),
                new ThreadFactoryBuilder()
                        .setNameFormat("retry-worker-%d")
                        .setDaemon(true)
                        .build()
        );

        // 任务执行线程池
        this.taskExecutor = new ThreadPoolExecutor(
                maxConcurrent,
                maxConcurrent,
                0L, TimeUnit.MILLISECONDS,
                new LinkedBlockingQueue<>(),
                new ThreadFactoryBuilder()
                        .setNameFormat("retry-executor-%d")
                        .build()
        );


        startWorkers();

        log.info("自动重试Worker线程池启动完成");
    }

    /**
     * 启动Worker线程
     */
    private void startWorkers() {
        for (int i = 0; i < workerThreads; i++) {
            final int workerId = i;

            workerPool.submit(() -> {
                log.info("Worker-{} 已启动，等待任务...", workerId);

                while (running && !Thread.currentThread().isInterrupted()) {
                    try {
                        // 1. 从数据库中取retry任务
                        ReEmbeddingRetryTask task = reEmbeddingRetryTaskService.getRetryTask();
                        if (Objects.isNull(task)) {
                            Thread.sleep(3000);
                            continue;
                        }
                        log.debug("Worker-{} 获取到任务: {}", workerId, task.getRetryTaskId());

                        // 2. 等待semaphore许可
                        semaphore.acquire();

                        log.debug("Worker-{} 获得执行许可: {}", workerId, task.getRetryTaskId());
                        // 3. 提交到执行线程池
                        taskExecutor.submit(() -> executeTask(task, workerId));

                    } catch (InterruptedException e) {
                        Thread.currentThread().interrupt();
                        log.info("Worker-{} 被中断，停止运行", workerId);
                        break;
                    } catch (Exception e) {
                        log.error("Worker-{} 发生异常", workerId, e);
                        try {
                            Thread.sleep(3000);
                        } catch (InterruptedException ie) {
                            Thread.currentThread().interrupt();
                            break;
                        }
                    }
                }

                log.info("Worker-{} 已停止", workerId);
            });
        }
    }

    /**
     * 执行任务（带重试逻辑）
     */
    private void executeTask(ReEmbeddingRetryTask task, int workerId) {
        log.info("executeTask start id={}, permits={}", workerId, semaphore.availablePermits());

        RLock lock = redissonClient.getLock(buildLockKey(task.getRetryTaskId()));
        boolean locked = false;
        try {
            locked = lock.tryLock(1, 10, TimeUnit.MINUTES);
            if (!locked) {
                // 别的实例已经在执行这个任务了，本次直接跳过即可
                log.info("Worker-{} 获取任务 {} 分布式锁失败，可能已有其他实例在执行，跳过", workerId, task.getRetryTaskId());
                return;
            }
            log.info("开始执行任务,retryTaskId={}", task.getRetryTaskId());
            Long fileId = task.getFileId();
            // 检查任务是否超时
            if (checkTimeout(task, workerId, fileId)) {
                //超时了最后要做迁移，否则下次点击文件解析不会成功
                ReEmbeddingRetryTaskDO latest = reEmbeddingRetryTaskService.getById(task.getRetryTaskId());
                RetryPayload retryPayload = JSONObject.parseObject(latest.getPayload(), RetryPayload.class);
                reEmbeddingFileService.markStatus(retryPayload.getKbId(), task.getTaskId(), fileId, ReEmbeddingTaskEnums.PARSED_FAIL);
                doMigrate(task, latest);
                return;
            }
            reEmbeddingRetryTaskService.incrRetryTimes(task.getRetryTaskId());

            ReEmbeddingRetryTaskDO latest = reEmbeddingRetryTaskService.getById(task.getRetryTaskId());
            log.info("增加了重试次数. retryTaskId={}, retryTimes={}", task.getRetryTaskId(), latest.getRetryTimes());
            knowledgeBaseListAppService.updateParseStatusByIds(List.of(fileId), KbFileStatusEnums.RE_EMBEDDING_ING.getValue(), true);
            log.info("Worker-{} 开始执行任务: {}, 第{}次尝试",
                    workerId, task.getRetryTaskId(), latest.getRetryTimes());
            long startTime = System.currentTimeMillis();

            long duration;
            try {
                // 执行实际任务
                try {
                    task.getRunnable().run();
                } catch (Throwable t) {
                    log.error(t.getMessage(), t);
                    // 保证 future 一定终态，join 不会永远等
                    task.getFuture().completeExceptionally(t);
                }

                duration = System.currentTimeMillis() - startTime;
                task.getFuture().join();
                log.info("Worker-{} 任务执行成功: {}, 耗时: {}ms",
                        workerId, task.getRetryTaskId(), duration);
                //处理成功
                handleSuccess(task, fileId, latest);
            } catch (CancellationException | CompletionException ce) {
                duration = System.currentTimeMillis() - startTime;
                Throwable cause = ce.getCause();
                String lastErrorMessage = (cause == null ? "未知异常" : cause.toString());
                log.error("Worker-{} 重试任务执行失败: {}, 耗时: {}ms, 具体异常: {}",
                        workerId, task.getRetryTaskId(), duration, lastErrorMessage,
                        cause);
                // 重试逻辑
                handleFailure(task, ce);
            }


        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            reEmbeddingRetryTaskService.updateStatus(task.getRetryTaskId(), ReEmbeddingRetryEnums.WAITING_NEXT.getCode(), null);
            log.warn("Worker-{} 获取任务 {} 分布式锁被中断", workerId, task.getRetryTaskId(), e);
        } catch (Exception e) {
            // 重试逻辑
            handleFailure(task, e);
        } finally {
            // 释放许可
            semaphore.release();
            try {
                if (locked && lock.isHeldByCurrentThread()) {
                    lock.unlock();
                    log.info("Worker-{} 释放分布式锁 任务:{}", workerId, task.getRetryTaskId());
                }
            } catch (Exception unlockEx) {
                log.warn("Worker-{} 释放任务 {} 分布式锁异常", workerId, task.getRetryTaskId(), unlockEx);
            }
            log.debug("Worker-{} 释放执行许可: {}", workerId, task.getRetryTaskId());
            log.info("executeTask end id={}, permits={}", workerId, semaphore.availablePermits());
        }
    }


    private void handleSuccess(ReEmbeddingRetryTask task, Long fileId, ReEmbeddingRetryTaskDO latest) {
        reEmbeddingRetryTaskService.updateStatus(task.getRetryTaskId(), ReEmbeddingRetryEnums.SUCCEED.getCode(), null);
        RetryPayload retryPayload = JSONObject.parseObject(latest.getPayload(), RetryPayload.class);
        reEmbeddingFileService.markStatus(retryPayload.getKbId(), retryPayload.getTaskId(), fileId, ReEmbeddingTaskEnums.PARSED_SUCCESS);
        doMigrate(task, latest);
    }

    private void doMigrate(ReEmbeddingRetryTask task, ReEmbeddingRetryTaskDO latest) {
        RLock lock = redissonClient.getLock(buildMigrateLockKey(task.getTaskId()));
        boolean locked = false;
        try {
            locked = lock.tryLock(1, 10, TimeUnit.MINUTES);
            if (!locked) {
                // 别的实例已经在执行这个任务了，本次直接跳过即可
                log.info("获取任务 {} 分布式锁失败，可能已有其他实例在执行，跳过", task.getRetryTaskId());
                return;
            }
            log.info("获取taskId{}分布式锁", task.getTaskId());
            ProcessFilePayload processFilePayload = JSONObject.parseObject(latest.getPayload(), ProcessFilePayload.class);
            int nonProcessedCount = reEmbeddingFileService.getNonProcessedFileCount(task.getTaskId(), processFilePayload.getKbId());
            if (task.getType().equals(RetryTaskEnums.FILE.getCode()) && nonProcessedCount == 0) {
                log.info("开始迁移");
                reEmbeddingTaskService.updateStatus(task.getTaskId(), ReEmbeddingTaskEnums.PARSED_SUCCESS);
                reEmbeddingTaskService.doMigrate(fileProcessExecutor, processFilePayload.getKbName(), processFilePayload.getCollectionName(), processFilePayload.getEmbeddingModelInfo(), processFilePayload.getKbId(), processFilePayload.getTaskId(), null);
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            log.warn("获取任务taskId:{} 分布式锁被中断", task.getTaskId(), e);
        } finally {
            try {
                if (locked && lock.isHeldByCurrentThread()) {
                    lock.unlock();
                    log.info("迁移 释放分布式锁 任务taskId:{}", task.getTaskId());
                }
            } catch (Exception unlockEx) {
                log.warn("迁移 释放分布式锁 任务taskId:{} 分布式锁异常", task.getTaskId());
            }
        }

    }


    private boolean checkTimeout(ReEmbeddingRetryTask task, int workerId, Long fileId) {
        if (System.currentTimeMillis() - task.getGmtCreate().getTime() > TimeUnit.MINUTES.toMillis(timeoutMinutes)) {
            log.info("Worker-{} 任务 {} 已超时 ({} 分钟)，标记为失败", workerId, task.getRetryTaskId(), timeoutMinutes);
            reEmbeddingRetryTaskService.updateStatus(task.getRetryTaskId(), ReEmbeddingRetryEnums.FAIL.getCode(), "任务执行超时");
            knowledgeBaseListAppService.updateParseStatusByIds(List.of(fileId), KbFileStatusEnums.PARSE_FAIL.getValue(), true);
            clearChunks(task.getKbName(), task.getCollectionName(), task.getFileId(), Objects.requireNonNull(RetryTaskEnums.of(task.getType())));
            return true;
        }
        return false;
    }


    /**
     * 处理失败：自动重试或标记失败
     */
    private void handleFailure(ReEmbeddingRetryTask task, Exception error) {
        if (Objects.isNull(task)) {
            return;
        }
        ReEmbeddingRetryTaskDO latest = reEmbeddingRetryTaskService.getById(task.getRetryTaskId());

        RetryPayload retryPayload = JSONObject.parseObject(latest.getPayload(), RetryPayload.class);
        Long fileId = retryPayload.getFileId();

        log.info("retry taskId:{} , currentRetryTimes:{}", task.getRetryTaskId(), latest.getRetryTimes());
        if (latest.getRetryTimes() < maxRetries) {
            //等待调度
            log.info("retry taskId:{}, change status: waiting_next", task.getRetryTaskId());
            reEmbeddingFileService.markStatus(fileId, ReEmbeddingTaskEnums.PARSING);
            reEmbeddingRetryTaskService.updateStatus(task.getRetryTaskId(), ReEmbeddingRetryEnums.WAITING_NEXT.getCode(), truncateForText(error.getMessage(), maxLength));
            knowledgeBaseListAppService.updateParseStatusByIds(List.of(task.getFileId()), KbFileStatusEnums.RE_EMBEDDING_ING.getValue(), true);
        } else {
            // 达到最大重试次数，标记为失败
            reEmbeddingFileService.markStatus(fileId, ReEmbeddingTaskEnums.PARSED_FAIL);
            knowledgeBaseListAppService.updateParseStatusByIds(List.of(task.getFileId()), KbFileStatusEnums.PARSE_FAIL.getValue(), true);
            log.error("任务最终失败，已达最大重试次数: {}", task.getRetryTaskId());
            task.getFuture().completeExceptionally(new ApplicationException(ErrCodeEnum.RETRY_TIMES_EXCEEDED));
            //处理失败
            reEmbeddingRetryTaskService.updateStatus(task.getRetryTaskId(), ReEmbeddingRetryEnums.FAIL.getCode(), truncateForText(error.getMessage(), maxLength));
            clearChunks(retryPayload.getKbName(), retryPayload.getKbName() + "_" + task.getTaskId(), retryPayload.getFileId(), Objects.requireNonNull(RetryTaskEnums.of(retryPayload.getType())));
            doMigrate(task, latest);
        }
    }

    private void clearChunks(String kbName, String collectionName, Long fileId, RetryTaskEnums type) {
        if (type.equals(RetryTaskEnums.FILE)) {
            List<String> collectionNames = IndexConstant.getCollectionNames(kbName);
            List<String> newCollectionNames = IndexConstant.getNewCollectionNames(collectionName);
            for (int i = 0; i < collectionNames.size(); i++) {
                String oldCollectionName = collectionNames.get(i);
                String newCollectionName = newCollectionNames.get(i);
                log.error("文件重试超过最大次数，执行清除es和milvus中{}的数据...准备delDocByCol{}和{}", fileId, oldCollectionName, newCollectionName);
                pyEsClient.delDocByCol(new PyEsIndex(oldCollectionName, fileId));
                pyMilvusClient.delDocByCol(new PyCollection(oldCollectionName, fileId));
                pyEsClient.delDocByCol(new PyEsIndex(newCollectionName, fileId));
                pyMilvusClient.delDocByCol(new PyCollection(newCollectionName, fileId));
            }
        }
    }

    /**
     * 优雅停机
     */
    @Override
    public void destroy() throws Exception {
        log.info("开始关闭自动重试Worker线程池...");

        running = false;

        // 2. 停止worker线程池
        workerPool.shutdown();

        // 3. 等待任务执行完成
        taskExecutor.shutdown();
        boolean terminated = taskExecutor.awaitTermination(30, TimeUnit.SECONDS);

        if (terminated) {
            log.info("自动重试Worker线程池已正常关闭");
        } else {
            log.warn("关闭超时，强制关闭");
            taskExecutor.shutdownNow();
        }
    }


    private void deleteOldEsDoc(String kbName, Long fileId) {
        PyEsIndex pyEsIndex = new PyEsIndex(kbName, fileId);
        try {
            log.info("es del doc by fileId, params:{}", objectMapper.writeValueAsString(pyEsIndex));
            PyEsResponse<Object> objectPyEsResponse = pyEsClient.delDocByCol(pyEsIndex);
            log.info("es del doc by fileId, response:{}", objectMapper.writeValueAsString(objectPyEsResponse));
        } catch (JsonProcessingException e) {
            throw new RuntimeException(e);
        }
    }

    /**
     * 截断字符串以适应 TEXT 字段（按字节截断）
     */
    private String truncateForText(String text, int maxBytes) {
        if (text == null) {
            return null;
        }

        try {
            byte[] bytes = text.getBytes("UTF-8");
            if (bytes.length <= maxBytes) {
                return text;
            }

            // 从 maxBytes 位置往前找，避免截断多字节字符
            int length = maxBytes;
            while (length > 0) {
                String truncated = new String(bytes, 0, length, "UTF-8");
                // 检查是否有乱码（截断了多字节字符）
                if (truncated.getBytes("UTF-8").length <= maxBytes) {
                    return truncated;
                }
                length--;
            }
            return "";
        } catch (Exception e) {
            return text.substring(0, Math.min(text.length(), maxBytes / 3));
        }
    }
}
