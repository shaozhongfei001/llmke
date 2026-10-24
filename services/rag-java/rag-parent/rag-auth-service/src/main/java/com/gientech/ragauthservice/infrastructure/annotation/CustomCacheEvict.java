package com.gientech.ragauthservice.infrastructure.annotation;

import java.lang.annotation.*;

@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface CustomCacheEvict {
    String cacheName();      // 缓存名（前缀）
    String key();            // 支持SpEL表达式
}
