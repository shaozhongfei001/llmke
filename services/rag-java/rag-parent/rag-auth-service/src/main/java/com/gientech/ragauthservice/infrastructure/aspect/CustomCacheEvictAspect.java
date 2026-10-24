package com.gientech.ragauthservice.infrastructure.aspect;

import com.gientech.ragauthservice.infrastructure.annotation.CustomCacheEvict;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.reflect.MethodSignature;
import org.redisson.api.RBucket;
import org.redisson.api.RedissonClient;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.DefaultParameterNameDiscoverer;
import org.springframework.core.ParameterNameDiscoverer;
import org.springframework.expression.EvaluationContext;
import org.springframework.expression.ExpressionParser;
import org.springframework.expression.spel.standard.SpelExpressionParser;
import org.springframework.expression.spel.support.StandardEvaluationContext;
import org.springframework.stereotype.Component;

import java.lang.reflect.Method;

/**
 * @author chenjuan
 * @date 2025/4/8 14:44
 */
@Aspect
@Component
public class CustomCacheEvictAspect {

    @Autowired
    private RedissonClient redissonClient;

    private final ExpressionParser parser = new SpelExpressionParser();
    private final ParameterNameDiscoverer nameDiscoverer = new DefaultParameterNameDiscoverer();

    @Around("@annotation(customCacheEvict)")
    public Object handleEviction(ProceedingJoinPoint pjp, CustomCacheEvict customCacheEvict) throws Throwable {
        Method method = ((MethodSignature) pjp.getSignature()).getMethod();
        Object[] args = pjp.getArgs();

        // 构建 SpEL 上下文
        EvaluationContext context = new StandardEvaluationContext();
        String[] paramNames = nameDiscoverer.getParameterNames(method);
        if (paramNames != null) {
            for (int i = 0; i < paramNames.length; i++) {
                context.setVariable(paramNames[i], args[i]);
            }
        }

        // 解析 key
        String dynamicKey = parser.parseExpression(customCacheEvict.key()).getValue(context, String.class);
        String finalKey = customCacheEvict.cacheName() + "::" + dynamicKey;

        // 执行数据库更新
        Object result = pjp.proceed();

        // 删除缓存
        RBucket<Object> bucket = redissonClient.getBucket(finalKey);
        bucket.delete();

        return result;
    }
}
