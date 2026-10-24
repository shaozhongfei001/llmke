package com.gientech.ragindexservice.application.job;

import com.gientech.ragindexservice.application.service.FileParseTaskAppService;
import lombok.extern.slf4j.Slf4j;
import org.redisson.api.RLock;
import org.redisson.api.RedissonClient;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.util.concurrent.TimeUnit;

@Slf4j
@Component
public class FileParseTaskScheduler {

    @Autowired
    private FileParseTaskAppService taskAppService;
    @Autowired
    private RedissonClient redissonClient;
    private static final String LOCK_PREFIX = "schedule:lock:";

    /**
     * Cron表达式执行：每10s执行一次
     */
//    @Scheduled(cron = "0 */1 * * * ?")
    @Scheduled(cron = "*/15 * * * * ?")
    public void scheduleTaskWithCronExpression() {
        log.info("定时器开始执行文件解析任务");
        String lockKey = "doc_parse_bak";
        RLock lock = redissonClient.getLock(LOCK_PREFIX + lockKey);
        try {
            // 尝试获取锁（不等待，锁超时5秒）
            if (lock.tryLock(0, 5, TimeUnit.SECONDS)) {
                taskAppService.execTask();
            }


    } catch (Exception e) {
        log.error("执行文档解析任务失败", e);
    }
        log.info("定时器成功执行文件解析任务");
    }
}
    