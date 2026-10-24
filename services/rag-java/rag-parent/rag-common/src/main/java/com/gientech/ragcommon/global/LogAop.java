package com.gientech.ragcommon.global;

import jakarta.servlet.http.HttpServletRequest;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.annotation.Pointcut;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;


@Aspect
@Component
@Order(1)
public class LogAop {

    private  Logger logger = LoggerFactory.getLogger(this.getClass());

    private static String VERTICAL_LINE = "|";

    @Pointcut(value = "(@within(org.springframework.web.bind.annotation.RestController) " +
            "   || @within(org.springframework.stereotype.Controller))" )
    public void pointcut() {
    }

    @Around("pointcut()")
    public Object doAround(ProceedingJoinPoint point) throws Throwable {
        Object result = null;
        long start = 0L;
        long end = 0L;
        StringBuilder logInfo = new StringBuilder(VERTICAL_LINE);
        try {
            ServletRequestAttributes attributes = (ServletRequestAttributes) RequestContextHolder.getRequestAttributes();
            HttpServletRequest request = attributes.getRequest();
            String requestURI = request.getRequestURI();
            logInfo.append(requestURI).append(VERTICAL_LINE);
            start = System.currentTimeMillis();
            result = point.proceed();
            end = System.currentTimeMillis();
            logInfo.append(end-start).append(VERTICAL_LINE);
            logInfo.append(true).append(VERTICAL_LINE);
        } catch (Exception e) {
            end = System.currentTimeMillis();
            logInfo.append(end-start).append(VERTICAL_LINE);
            logInfo.append(false).append(VERTICAL_LINE);
            result = CommonResponse.fail(ErrCodeEnum.UNKNOWN);
            throw e;
        } finally {
            logger.info(logInfo.toString());
        }
        return result;
    }

}
