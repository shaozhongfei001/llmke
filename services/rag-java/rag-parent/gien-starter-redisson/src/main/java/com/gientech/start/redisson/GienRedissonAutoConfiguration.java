package com.gientech.start.redisson;

import com.gientech.start.redisson.utils.RedissonUtils;
import org.redisson.Redisson;
import org.redisson.api.RedissonClient;
import org.redisson.config.Config;
import org.redisson.config.SingleServerConfig;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.context.annotation.Bean;
import org.springframework.util.StringUtils;

/**
 * R12 兼容自动装配：从 spring.data.redis.* 构造 RedissonClient（单机模式）。
 * 与原内网 starter 的差异：不依赖其内部 properties 结构，读取 Boot 标准 redis 配置键。
 */
@AutoConfiguration
public class GienRedissonAutoConfiguration {

    @Bean(destroyMethod = "shutdown")
    @ConditionalOnMissingBean(RedissonClient.class)
    public RedissonClient redissonClient(
            @Value("${spring.data.redis.host:127.0.0.1}") String host,
            @Value("${spring.data.redis.port:6379}") int port,
            @Value("${spring.data.redis.password:}") String password,
            @Value("${spring.data.redis.database:0}") int database,
            @Value("${spring.data.redis.timeout:5000}") int timeout) {
        Config config = new Config();
        SingleServerConfig server = config.useSingleServer()
                .setAddress("redis://" + host + ":" + port)
                .setDatabase(database)
                .setTimeout(timeout)
                .setConnectionMinimumIdleSize(4)
                .setConnectionPoolSize(16);
        if (StringUtils.hasText(password)) {
            server.setPassword(password);
        }
        return Redisson.create(config);
    }

    @Bean
    @ConditionalOnMissingBean(RedissonUtils.class)
    public RedissonUtils redissonUtils(RedissonClient redissonClient) {
        return new RedissonUtils(redissonClient);
    }

    @Bean
    @ConditionalOnMissingBean(com.gientech.start.redisson.lock.RedissonLock.class)
    public com.gientech.start.redisson.lock.RedissonLock redissonLock(RedissonClient redissonClient) {
        return new com.gientech.start.redisson.lock.RedissonLock(redissonClient);
    }
}
