package com.gientech.ragauthservice.infrastructure.aspect;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.gientech.ragauthservice.infrastructure.annotation.CustomCacheable;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.reflect.MethodSignature;
import org.redisson.api.RBucket;
import org.redisson.api.RedissonClient;
import org.redisson.codec.JsonJacksonCodec;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.DefaultParameterNameDiscoverer;
import org.springframework.core.ParameterNameDiscoverer;
import org.springframework.expression.EvaluationContext;
import org.springframework.expression.ExpressionParser;
import org.springframework.expression.spel.standard.SpelExpressionParser;
import org.springframework.expression.spel.support.StandardEvaluationContext;
import org.springframework.stereotype.Component;

import java.lang.reflect.Method;
import java.lang.reflect.Parameter;
import java.util.concurrent.TimeUnit;

/**
 * @author chenjuan
 * @date 2025/4/2 14:40
 */
@Aspect
@Component
public class CustomCacheableAspect {
    @Autowired
    private RedissonClient redissonClient;

    private final ExpressionParser parser = new SpelExpressionParser();

    @Around("@annotation(customCacheable)")
    public Object around(ProceedingJoinPoint pjp, CustomCacheable customCacheable) throws Throwable {
        Method method = ((MethodSignature) pjp.getSignature()).getMethod();
        EvaluationContext context = buildContext(method, pjp.getArgs());
        String key = customCacheable.cacheName() + "::" + parser.parseExpression(customCacheable.key()).getValue(context, String.class);

        RBucket<Object> bucket = redissonClient.getBucket(key, JsonJacksonCodec.INSTANCE);
        Object cached = bucket.get();
        if (cached != null) {
            Class<?> returnType = method.getReturnType();
            ObjectMapper objectMapper = new ObjectMapper();
            return objectMapper.convertValue(cached, returnType);
        }

        // 执行方法并缓存
        Object result = pjp.proceed();
        if (result != null) {
            bucket.set(result, customCacheable.ttl(), TimeUnit.SECONDS);
        }
        return result;
    }

    private EvaluationContext buildContext(Method method, Object[] args) {
        EvaluationContext context = new StandardEvaluationContext();
        Parameter[] paramNames = method.getParameters();
        if (paramNames != null) {
            for (int i = 0; i < paramNames.length; i++) {
                context.setVariable(paramNames[i].getName(), args[i]);
            }
        }
        return context;
    }
}
