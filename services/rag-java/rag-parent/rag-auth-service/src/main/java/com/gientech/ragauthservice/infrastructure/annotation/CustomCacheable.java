package com.gientech.ragauthservice.infrastructure.annotation;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface CustomCacheable {
    String cacheName();           // 缓存命名空间
    String key();                 // 缓存key，支持SpEL
    long ttl() default 1200;        // 缓存过期时间（秒）
}
