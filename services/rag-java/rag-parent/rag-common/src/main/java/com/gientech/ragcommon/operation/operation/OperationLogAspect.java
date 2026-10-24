package com.gientech.ragcommon.operation.operation;

import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragcommon.operation.annotation.OperationLog;
import com.gientech.ragcommon.operation.model.UserOperateDO;
import com.gientech.ragcommon.operation.service.UserOperateService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.springframework.stereotype.Component;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.Arrays;
import java.util.Date;
import java.util.Objects;

/**
 * @Descrption:
 * @Author:liutaiyun
 * @Date:2024/12/24 11:07
 **/

@Aspect
@Component
@Slf4j
public class OperationLogAspect {
    private final UserOperateService userOperateService;

    public OperationLogAspect(UserOperateService userOperateService) {
        this.userOperateService = userOperateService;
    }

    @Around(value = "@annotation(operationLog)", argNames = "joinPoint,operationLog")
    public Object log(ProceedingJoinPoint joinPoint, OperationLog operationLog) throws Throwable {
        LocalDateTime startTime = LocalDateTime.now();
        Object proceed = joinPoint.proceed();
        LocalDateTime endTime = LocalDateTime.now();
        insertOperationLog(joinPoint, operationLog, startTime, endTime);
        return proceed;
    }

    private void insertOperationLog(ProceedingJoinPoint joinPoint, OperationLog operationLog, LocalDateTime startTime, LocalDateTime endTime) {
        //操作类型
        String operateType = operationLog.operateType();
//        log.info("operation log:{}", operateType);
        //方法名称
        String name = joinPoint.getSignature().getName();
//        log.info("operation name:{}", name);
        //获取方法参数
        Object[] args = joinPoint.getArgs();
        String argsString = Arrays.toString(args);
//        log.info("operation argsString:{}", argsString);

        //获取用户id,username
        HttpServletRequest request = ((ServletRequestAttributes) RequestContextHolder.getRequestAttributes()).getRequest();
        HttpServletResponse response = ((ServletRequestAttributes) RequestContextHolder.getRequestAttributes()).getResponse();
        String userId = request.getHeader("userId");
//        log.info("operation userId:{}", userId);
        String userName = request.getHeader("userName");
        User user = UserContext.getUser();
        if(!Objects.isNull(user)){
            userName = user.getUserName();
            userId = user.getUserId();
        }
//        log.info("operation userName:{}", userName);
        String url = request.getRequestURL().toString();
//        log.info("operation url:{}", url);
        String ip = request.getRemoteAddr();
        int status = response.getStatus();
        log.info("status is:{}",status);
        UserOperateDO userOperateDO = UserOperateDO.builder()
                .url(url)
                .gmtCreated(localDateTime2Date(endTime))
                .gmtModified(localDateTime2Date(endTime))
                .params(argsString)
                .userId(StringUtils.isNotEmpty(userId)?Long.valueOf(userId):null)
                .userName(userName)
                .startTime(localDateTime2Date(startTime))
                .endTime(localDateTime2Date(endTime))
                .name(operateType)
                .ip(ip)
                .success(status == 200 ? 1 : 0)
                .build();
        userOperateService.save(userOperateDO);
    }

    private Date localDateTime2Date(LocalDateTime localDateTime) {
        ZoneId zoneId = ZoneId.systemDefault();
        return Date.from(localDateTime.atZone(zoneId).toInstant());
    }
}
