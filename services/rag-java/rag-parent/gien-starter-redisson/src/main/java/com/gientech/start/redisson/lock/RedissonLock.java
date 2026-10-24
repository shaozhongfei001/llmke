package com.gientech.start.redisson.lock;

import org.redisson.api.RLock;
import org.redisson.api.RedissonClient;

import java.util.concurrent.TimeUnit;

/**
 * 分布式锁工具（R12 兼容实现）。
 * 注意：原内网 starter 中的 RedissonLock 是「可注入的工具 Bean」，不是注解；
 * 调用方存在 {@code @Autowired private RedissonLock redissonLock;} 的声明（调用点已注释），
 * 因此这里按 Bean 形态实现，保持类型可注入。
 */
public class RedissonLock {

    private final RedissonClient redissonClient;

    public RedissonLock(RedissonClient redissonClient) {
        this.redissonClient = redissonClient;
    }

    public void lock(String lockName) {
        RLock lock = redissonClient.getLock(lockName);
        lock.lock();
    }

    public void lock(String lockName, long leaseTime, TimeUnit unit) {
        redissonClient.getLock(lockName).lock(leaseTime, unit);
    }

    public boolean tryLock(String lockName, long waitTime, long leaseTime, TimeUnit unit) {
        try {
            return redissonClient.getLock(lockName).tryLock(waitTime, leaseTime, unit);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            return false;
        }
    }

    public void unlock(String lockName) {
        RLock lock = redissonClient.getLock(lockName);
        if (lock.isHeldByCurrentThread()) {
            lock.unlock();
        }
    }
}
