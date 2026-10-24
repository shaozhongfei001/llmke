package com.gientech.ragcommon.infrastructure.config;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.context.config.annotation.RefreshScope;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.task.TaskExecutor;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

/**
 * @Description:
 * @Author: chenjuan
 * @Date: 2024/8/30 13:38
 */
@Configuration
@EnableAsync
@RefreshScope
@Slf4j
public class AsyncConfig {

    @Value("${thread-pool.core-pool-size:16}")
    private int corePoolSize;
    @Value("${thread-pool.max-pool-size:32}")
    private int maxPoolSize;
    @Value("${thread-pool.queue-capacity:24}")
    private int queueCapacity;

    @Bean(name = "asyncExecutor")
    public TaskExecutor asyncExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(corePoolSize);
        executor.setMaxPoolSize(maxPoolSize);
        executor.setQueueCapacity(queueCapacity);
        executor.setThreadNamePrefix("AsyncThread-");
        executor.setAwaitTerminationSeconds(60 * 15);
        executor.setWaitForTasksToCompleteOnShutdown(true);
        executor.initialize();

        int cpuCount = Runtime.getRuntime().availableProcessors();
        log.info("cpu count:{}",cpuCount);
        return executor;
    }
}
