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
            // R14-C-FIX-32b：原来是 `tryLock(0, 5, SECONDS)` —— **显式 5 秒租约且不续期**。
            // execTask 内部是同步调解析（单个文件常远超 5 秒），锁会在解析中途自动过期，
            // 于是下一轮 cron（15s 后）在另一个线程/实例上重新拿到锁，把仍在解析的任务再取一次。
            // 改用 leaseTime = -1（Redisson watchdog 自动续期，进程活着就一直持有、进程挂了才释放）。
            if (lock.tryLock(0, -1, TimeUnit.SECONDS)) {
                taskAppService.execTask();
            }


    } catch (Exception e) {
        log.error("执行文档解析任务失败", e);
    }
        log.info("定时器成功执行文件解析任务");
    }
}
    