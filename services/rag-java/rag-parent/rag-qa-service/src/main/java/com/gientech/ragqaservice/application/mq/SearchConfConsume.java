//package com.gientech.ragqaservice.application.mq;
//
//import com.alibaba.fastjson2.JSON;
//import com.alibaba.fastjson2.JSONArray;
//import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
//import com.gientech.ragcommon.infrastructure.emuns.MessageChannel;
//import com.gientech.ragcommon.qa.enmus.SysTypeEnums;
//import com.gientech.ragcommon.qa.entity.Config;
//import com.gientech.ragqaservice.domain.entity.Dialogue;
//import com.gientech.ragqaservice.domain.service.DialogueDomainService;
//import com.gientech.ragqaservice.domain.service.SearchConfigDomainService;
//import lombok.extern.slf4j.Slf4j;
//import org.apache.commons.lang3.StringUtils;
//import org.apache.rocketmq.spring.annotation.MessageModel;
//import org.apache.rocketmq.spring.annotation.RocketMQMessageListener;
//import org.apache.rocketmq.spring.core.RocketMQListener;
//import org.springframework.beans.factory.annotation.Autowired;
//import org.springframework.stereotype.Component;
//import java.util.*;
//import java.util.concurrent.ExecutorService;
//import java.util.concurrent.Executors;
//
//@Slf4j
//@Component
//@RocketMQMessageListener(consumerGroup = MessageChannel.SEARCH_CONFIG_CHANGE_GROUP,
//        topic = MessageChannel.SEARCH_CONFIG_CHANGE_TOPIC, messageModel = MessageModel.CLUSTERING)
//public class SearchConfConsume implements RocketMQListener<Long> {
//
//    private ExecutorService threadPool = Executors.newFixedThreadPool(5);
//
//    @Autowired
//    private SearchConfigDomainService searchConfigDomainService;
//
//    @Autowired
//    private DialogueDomainService dialogueDomainService;
//
//
//    @Override
//    public void onMessage(Long configId) {
//        log.info("收到检索配置变更的id是:{}", configId);
//        if (Objects.isNull(configId)) {
//            log.error("configId为空");
//            return;
//        }
//
//        Config config = searchConfigDomainService.getConfigById(configId);
//        if (Objects.nonNull(config)) {
//            threadPool.execute(() -> {
//                try {
//                    //分批次处理,避免数据过大内存溢出
//                    Long pageNo = 1L;
//                    Long pageSize = 200L;
//                    Page<Dialogue> dialoguePage = dialogueDomainService.findListByConfId(configId, SysTypeEnums.INT_SESSION, pageNo, pageSize);
//                    List<Dialogue> dialogues = dialoguePage.getRecords();
//                    long size = dialogues.size();
//                    while (size > 0 && size <= pageSize) {
//                        dialogues.forEach(dialogue -> updateiDalogueConf(dialogue, config));
//                        pageNo++;
//                        dialoguePage = dialogueDomainService.findListByConfId(configId, SysTypeEnums.INT_SESSION, pageNo, pageSize);
//                        dialogues = dialoguePage.getRecords();
//                        size = dialogues.size();
//                    }
//                } catch (Exception e) {
//                    log.error(e.getMessage());
//                }
//            });
//        }
//    }
//
//    private void updateiDalogueConf(Dialogue dialogue, Config config) {
//        String configHistory = dialogue.getConfigHistory();
//        if (StringUtils.isNotBlank(configHistory)) {
//            JSONArray histories = JSON.parseArray(configHistory);
//            histories.add(config);
//            dialogue.setConfigHistory(JSON.toJSONString(histories));
//        }else {
//            dialogue.setConfigHistory(JSON.toJSONString(Arrays.asList(config)));
//        }
//        dialogueDomainService.updateById(dialogue);
//    }
//}
