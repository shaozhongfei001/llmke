//package com.gientech.ragindexservice.application.mq;
//
//import com.alibaba.fastjson2.JSON;
//import com.alibaba.fastjson2.JSONObject;
//import com.gientech.ragcommon.index.enmus.KbFileStatusEnums;
//import com.gientech.ragcommon.infrastructure.emuns.MessageChannel;
//import com.gientech.ragindexservice.domain.entity.KnowledgeBase;
//import com.gientech.ragindexservice.domain.entity.KnowledgeBaseList;
//import com.gientech.ragindexservice.domain.service.KnowledgeBaseDomainService;
//import com.gientech.ragindexservice.domain.service.KnowledgeBaseListDomainService;
//import com.gientech.ragindexservice.infrastructure.RemoteFileUtils;
//import com.google.common.collect.Lists;
//import lombok.extern.slf4j.Slf4j;
//import org.apache.rocketmq.spring.annotation.MessageModel;
//import org.apache.rocketmq.spring.annotation.RocketMQMessageListener;
//import org.apache.rocketmq.spring.core.RocketMQListener;
//import org.springframework.beans.factory.annotation.Autowired;
//import org.springframework.stereotype.Component;
//import org.springframework.util.CollectionUtils;
//import java.util.*;
//import java.util.concurrent.ExecutorService;
//import java.util.concurrent.Executors;
//
//@Slf4j
//@Component
//@RocketMQMessageListener(consumerGroup = MessageChannel.KB_CONFIG_CHANGE_GROUP,
//        topic = MessageChannel.KB_CONFIG_CHANGE_TOPIC, messageModel = MessageModel.CLUSTERING)
//public class KbConfConsume implements RocketMQListener<Long> {
//
//    @Autowired
//    private KnowledgeBaseDomainService knowledgeBaseDomainService;
//
//    @Autowired
//    private KnowledgeBaseListDomainService knowledgeBaseFileDomainService;
//
//    @Autowired
//    private RemoteFileUtils remoteFileUtils;
//
//    private ExecutorService threadPool = Executors.newFixedThreadPool(5);
//
//    @Override
//    public void onMessage(Long kbId) {
//        log.info("收到的知识库配置变更:{}", kbId);
//        if (Objects.isNull(kbId)) {
//            log.error("知识库id为空");
//            return;
//        }
//        KnowledgeBase kb = knowledgeBaseDomainService.findByKbId(kbId);
//        List<KnowledgeBaseList> kbFiles = knowledgeBaseFileDomainService.findFileByKbId(kbId);
//        if (Objects.isNull(kb) || CollectionUtils.isEmpty(kbFiles)) {
//            log.warn("知识库已经被删除,无需解析");
//            return;
//        }
//        doFilesParse(kb, kbFiles);
//    }
//
//    private void doFilesParse(KnowledgeBase kb, List<KnowledgeBaseList> kbFiles) {
//        String config = kb.getConfig();
//        JSONObject configJson = JSON.parseObject(config);
//        kbFiles.forEach(kbFile -> {
//            String filePath = kbFile.getFilePath();
//            Map<String, Object> paraMap = new HashMap<>();
//            paraMap.put("chunk_overlap", 20);
//            paraMap.put("kb_id", kbFile.getFileSize());
//            paraMap.put("chunk_size", configJson.getInteger("chunkSize"));
//            paraMap.put("embedding_model_name", configJson.getString("embeddingModelName"));
//            paraMap.put("file_type", configJson.getString("fileType"));
//            paraMap.put("file_paths", Arrays.asList(filePath.substring(filePath.indexOf("/", 10) + 1)));
//            paraMap.put("knowledge_base_name", kb.getPrimitiveName());
//            threadPool.execute(() -> {
//                try {
//                    knowledgeBaseFileDomainService.updateStatusByFilePaths(Lists.newArrayList(filePath), KbFileStatusEnums.PARSE_ING.getValue());
//                    // TODO: 2024/8/8 确认下写入方式，保证向量库和ES库中同一份文件至于一份数据
//                    String parseResult = remoteFileUtils.fileParse(JSON.toJSONString(paraMap));
//                    JSONObject jsonObject = JSON.parseObject(parseResult);
//                    Boolean isSuccess = jsonObject.getBoolean("success");
//                    if (isSuccess) {
//                        knowledgeBaseFileDomainService.updateStatusByFilePaths(Lists.newArrayList(filePath), KbFileStatusEnums.PARSE_SUCCESS.getValue());
//                    } else {
//                        log.error("文档解析失败【" + filePath + "】");
//                        knowledgeBaseFileDomainService.updateStatusByFilePaths(Lists.newArrayList(filePath), KbFileStatusEnums.PARSE_FAIL.getValue());
//                    }
//                } catch (Exception e) {
//                    log.error("文档解析失败【" + filePath + "】,异常原因【" + e.getMessage() + "】");
//                    knowledgeBaseFileDomainService.updateStatusByFilePaths(Lists.newArrayList(filePath), KbFileStatusEnums.PARSE_FAIL.getValue());
//                }
//            });
//        });
//    }
//}
