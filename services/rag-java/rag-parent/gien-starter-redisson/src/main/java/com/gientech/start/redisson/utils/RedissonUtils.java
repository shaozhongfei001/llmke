package com.gientech.start.redisson.utils;

import org.redisson.api.RBucket;
import org.redisson.api.RMap;
import org.redisson.api.RScoredSortedSet;
import org.redisson.api.RedissonClient;

import java.time.Duration;
import java.time.temporal.ChronoUnit;
import java.util.LinkedHashSet;
import java.util.Set;
import java.util.concurrent.TimeUnit;

/**
 * R12 兼容实现：等价替代内网 com.gientech:gien-starter-redisson 中的同名工具类。
 * 语义与调用方期望一致：key/value 为 String，超时单位为传入的 TimeUnit/ChronoUnit。
 * 见 docs/r12/ADAPTATIONS.md#A-02。
 */
public class RedissonUtils {

    private final RedissonClient redissonClient;

    public RedissonUtils(RedissonClient redissonClient) {
        this.redissonClient = redissonClient;
    }

    public RedissonClient getRedissonClient() {
        return redissonClient;
    }

    public void set(String key, String value) {
        redissonClient.getBucket(key).set(value);
    }

    public void set(String key, String value, long timeout, TimeUnit unit) {
        redissonClient.getBucket(key).set(value, Duration.ofMillis(unit.toMillis(timeout)));
    }

    public void set(String key, String value, long timeout, ChronoUnit unit) {
        redissonClient.getBucket(key).set(value, Duration.of(timeout, unit));
    }

    /** 兼容 CharSequence（StringBuffer/StringBuilder）写入，超时参数为包装类型。 */
    public void set(String key, CharSequence value, Long timeout, TimeUnit unit) {
        redissonClient.getBucket(key).set(value == null ? null : value.toString(),
                Duration.ofMillis(unit.toMillis(timeout)));
    }

    public void set(String key, CharSequence value, Long timeout, ChronoUnit unit) {
        redissonClient.getBucket(key).set(value == null ? null : value.toString(), Duration.of(timeout, unit));
    }

    public String get(String key) {
        RBucket<String> bucket = redissonClient.getBucket(key);
        return bucket.get();
    }

    public boolean exists(String key) {
        return redissonClient.getBucket(key).isExists();
    }

    public void deleteKey(String... keys) {
        if (keys == null || keys.length == 0) {
            return;
        }
        for (String key : keys) {
            redissonClient.getBucket(key).delete();
            redissonClient.getMap(key).delete();
            redissonClient.getScoredSortedSet(key).delete();
        }
    }

    public void expireKey(String key, long timeout, TimeUnit unit) {
        redissonClient.getBucket(key).expire(Duration.ofMillis(unit.toMillis(timeout)));
    }

    public void expireKey(String key, long timeout, ChronoUnit unit) {
        redissonClient.getBucket(key).expire(Duration.of(timeout, unit));
    }

    public void hashPut(String key, String field, String value) {
        redissonClient.getMap(key).put(field, value);
    }

    public void hashPut(String key, String field, String value, long timeout, TimeUnit unit) {
        RMap<String, String> map = redissonClient.getMap(key);
        map.put(field, value);
        map.expire(Duration.ofMillis(unit.toMillis(timeout)));
    }

    public void hashPut(String key, String field, String value, long timeout, ChronoUnit unit) {
        RMap<String, String> map = redissonClient.getMap(key);
        map.put(field, value);
        map.expire(Duration.of(timeout, unit));
    }

    public void hashPut(String key, java.util.Map<String, String> values, long timeout, ChronoUnit unit) {
        RMap<String, String> map = redissonClient.getMap(key);
        map.putAll(values);
        map.expire(Duration.of(timeout, unit));
    }

    public void hashPut(String key, java.util.Map<String, String> values, long timeout, TimeUnit unit) {
        RMap<String, String> map = redissonClient.getMap(key);
        map.putAll(values);
        map.expire(Duration.ofMillis(unit.toMillis(timeout)));
    }

    @SuppressWarnings("unchecked")
    public String hashGet(String key, String field) {
        RMap<Object, Object> map = redissonClient.getMap(key);
        Object value = map.get(field);
        return value == null ? null : String.valueOf(value);
    }

    public void hashDelete(String key, String... fields) {
        redissonClient.getMap(key).fastRemove(fields);
    }

    public void zscoreAddAsync(String key, double score, String member, Object extra) {
        RScoredSortedSet<Object> set = redissonClient.getScoredSortedSet(key);
        set.add(score, member);
    }

    public Set<Object> getFixZSetMembers(String key, int count) {
        RScoredSortedSet<Object> set = redissonClient.getScoredSortedSet(key);
        // 取分值最高（最近）的 count 条
        return new LinkedHashSet<>(set.valueRangeReversed(0, true, count - 1, true));
    }

    public void removeZSetMemberAsync(String key, String member) {
        redissonClient.getScoredSortedSet(key).remove(member);
    }

    public void removeAllZSetMembers(String key) {
        redissonClient.getScoredSortedSet(key).delete();
    }
}
