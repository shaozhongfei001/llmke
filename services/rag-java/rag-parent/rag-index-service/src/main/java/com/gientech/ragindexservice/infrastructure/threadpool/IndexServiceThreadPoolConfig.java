package com.gientech.ragindexservice.infrastructure.threadpool;

import cn.hutool.core.thread.ThreadFactoryBuilder;
import com.gientech.ragindexservice.application.service.KnowledgeBaseListAppService;
import com.gientech.ragindexservice.domain.service.ReEmbeddingFileService;
import com.gientech.ragindexservice.domain.service.ReEmbeddingRetryTaskService;
import com.gientech.ragindexservice.domain.service.ReEmbeddingTaskService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.context.config.annotation.RefreshScope;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;

/**
 * @author: shirleychen
 * @date 2025/12/1 13:46
 * @description
 */
@Configuration
@RefreshScope
@Slf4j
public class IndexServiceThreadPoolConfig {

    @Value("${re-embedding.thread-pool.queue-capacity:100}")
    private int queueCapacity;
    @Value("${re-embedding.thread-pool.core-pool-size:64}")
    private int corePoolSize;
    @Value("${re-embedding.thread-pool.maximum-pool-size:128}")
    private int maximumPoolSize;


    @Bean("fileProcessExecutor")
    public ThreadPoolExecutor fileProcessExecutor(ReEmbeddingRetryTaskService reEmbeddingRetryTaskService, ReEmbeddingTaskService reEmbeddingTaskService, KnowledgeBaseListAppService knowledgeBaseListAppService, ReEmbeddingFileService reEmbeddingFileService) {
        log.info("fileProcessExecutor,available processors: {}", Runtime.getRuntime().availableProcessors());
        //超时时间30分钟
        return new ThreadPoolExecutor(
                corePoolSize,
                maximumPoolSize,
                30L, TimeUnit.MINUTES,
                new LinkedBlockingQueue<>(queueCapacity),
                new ThreadFactoryBuilder().setNamePrefix("fileProcess-").build(), new PersistToMySqlRejectedExecutionHandler(reEmbeddingRetryTaskService, reEmbeddingTaskService, reEmbeddingFileService));
    }

    @Bean("reEmbeddingExecutor")
    public ThreadPoolExecutor embeddingExecutor(ReEmbeddingRetryTaskService reEmbeddingRetryTaskService, ReEmbeddingTaskService reEmbeddingTaskService, KnowledgeBaseListAppService knowledgeBaseListAppService, ReEmbeddingFileService reEmbeddingFileService) {
        log.info("reEmbeddingExecutor,available processors: {}", Runtime.getRuntime().availableProcessors());
        //超时时间30分钟
        return new ThreadPoolExecutor(
                corePoolSize,
                maximumPoolSize,
                30L, TimeUnit.MINUTES,
                new LinkedBlockingQueue<>(queueCapacity),
                new ThreadFactoryBuilder().setNamePrefix("reEmbedding-").build(), new PersistToMySqlRejectedExecutionHandler(reEmbeddingRetryTaskService, reEmbeddingTaskService, reEmbeddingFileService));
    }

    /**
     * 获取线程池可用容量
     */
    public static int getAvailableCapacity(ThreadPoolExecutor executor) {
        int maxPoolSize = executor.getMaximumPoolSize();
        int activeCount = executor.getActiveCount();
        int queueRemaining = executor.getQueue().remainingCapacity();

        // 可用容量 = (最大线程数 - 活跃线程数) + 队列剩余容量
        return Math.max(0, (maxPoolSize - activeCount) + queueRemaining);
    }
}
