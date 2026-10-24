//package com.gientech.ragindexservice.infrastructure;
//import com.alibaba.fastjson2.JSON;
//import com.alibaba.fastjson2.JSONObject;
//import com.gientech.ragcommon.index.request.KbConfUpdateReq;
//import com.gientech.ragcommon.infrastructure.emuns.MessageChannel;
//import com.gientech.ragindexservice.domain.entity.KnowledgeBase;
//import com.gientech.ragindexservice.domain.service.KnowledgeBaseDomainService;
//import lombok.extern.slf4j.Slf4j;
//import org.apache.commons.lang3.StringUtils;
//import org.apache.rocketmq.spring.core.RocketMQTemplate;
//import org.aspectj.lang.JoinPoint;
//import org.aspectj.lang.annotation.AfterReturning;
//import org.aspectj.lang.annotation.Aspect;
//import org.aspectj.lang.annotation.Before;
//import org.aspectj.lang.annotation.Pointcut;
//import org.springframework.aop.aspectj.MethodInvocationProceedingJoinPoint;
//import org.springframework.beans.factory.annotation.Autowired;
//import org.springframework.core.annotation.Order;
//import org.springframework.messaging.support.MessageBuilder;
//import org.springframework.stereotype.Component;
//
//@Slf4j
//@Component
//@Aspect
//@Order(-1)
//public class KbConfAspect {
//
//    @Autowired
//    private KnowledgeBaseDomainService knowledgeBaseDomainService;
//
//    @Autowired
//    private RocketMQTemplate rocketMQTemplate;
//
//    private KnowledgeBase knowledgeBase = null;
//
//    @Pointcut(value = "execution(* com.gientech.ragindexservice.interfaces.KnowledgeBaseController.updateConf(..))" )
//    public void point() {
//    }
//
//    @Before("point()")
//    public void doABefore(JoinPoint joinPoint){
//        try {
//            Object[] args = ((MethodInvocationProceedingJoinPoint) joinPoint).getArgs();
//            KbConfUpdateReq kbConfUpdateReq = (KbConfUpdateReq)args[0];
//            Long kbId = kbConfUpdateReq.getId();
//            knowledgeBase = knowledgeBaseDomainService.findByKbId(kbId);
//        } catch (Exception e) {
//            log.error(e.getMessage());
//        }
//    }
//
//    @AfterReturning("point()")
//    public void doAfterReturning(JoinPoint joinPoint){
//        try {
//            Object[] args = ((MethodInvocationProceedingJoinPoint) joinPoint).getArgs();
//            KbConfUpdateReq kbConfUpdateReq = (KbConfUpdateReq)args[0];
//            String config = knowledgeBase.getConfig();
//            if(StringUtils.isEmpty(config) || !isSameConf(kbConfUpdateReq,config)){
//                rocketMQTemplate.syncSend(MessageChannel.KB_CONFIG_CHANGE_TOPIC,MessageBuilder.withPayload(knowledgeBase.getId()).build());
//            }
//        } catch (Exception e) {
//            log.error(e.getMessage());
//        }
//    }
//
//    private Boolean isSameConf(KbConfUpdateReq kbConfUpdateReq, String config) {
//        Integer chunkSize = kbConfUpdateReq.getChunkSize();
//        String fileType = kbConfUpdateReq.getFileType();
//        String embeddingModelName = kbConfUpdateReq.getEmbeddingModelName();
//        JSONObject confJson = JSON.parseObject(config);
//        return chunkSize.equals(confJson.getInteger("chunkSize"))
//                && fileType.equals(confJson.getString("fileType"))
//                && embeddingModelName.equals(confJson.getString("embeddingModelName"));
//    }
//
//}
