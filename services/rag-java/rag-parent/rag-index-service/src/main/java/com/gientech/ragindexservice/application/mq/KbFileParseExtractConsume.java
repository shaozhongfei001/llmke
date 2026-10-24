//package com.gientech.ragindexservice.application.mq;
//
//import com.gientech.ragcommon.context.user.User;
//import com.gientech.ragcommon.context.user.UserContext;
//import com.gientech.ragcommon.index.enmus.MultiversionParseEnums;
//import com.gientech.ragcommon.index.enmus.ParseTypeEnums;
//import com.gientech.ragcommon.infrastructure.emuns.MessageChannel;
//import com.gientech.ragcommon.index.parameter.FileMessage;
//import com.gientech.ragindexservice.application.service.FileAppService;
//import lombok.extern.slf4j.Slf4j;
//import org.apache.rocketmq.spring.annotation.ConsumeMode;
//import org.apache.rocketmq.spring.annotation.MessageModel;
//import org.apache.rocketmq.spring.annotation.RocketMQMessageListener;
//import org.springframework.beans.factory.annotation.Autowired;
//import org.springframework.stereotype.Component;
//
//import java.util.Arrays;
//import java.util.stream.Collectors;
//
///**
// *
// */
//@Slf4j
//@Component
////@RocketMQMessageListener(consumerGroup = MessageChannel.KB_FILE_PARSE_EXTRACT_GROUP,
////        topic = MessageChannel.KB_FILE_PARSE_EXTRACT_TOPIC, messageModel = MessageModel.CLUSTERING)
//@RocketMQMessageListener(consumerGroup = MessageChannel.KB_FILE_PARSE_EXTRACT_GROUP,
//        topic = MessageChannel.KB_FILE_PARSE_EXTRACT_TOPIC, messageModel = MessageModel.CLUSTERING,
//        consumeMode = ConsumeMode.ORDERLY,consumeThreadNumber = 3,maxReconsumeTimes = 0
//)
//public class KbFileParseExtractConsume extends AbstarctKbFileConsume {
//
//    @Autowired
//    private FileAppService filesAppParse;
//
//    @Override
//    protected void dealFile(FileMessage param) {
//        log.info("收到消息：{}", param);
//
//        //设置用户上下文信息
//        User user = new User();
//        user.setUserId(param.getUserId());
//        user.setUserName(param.getUserName());
//        UserContext.setUser(user);
//
//        Boolean isExtract = param.getIsExtract();
//        //文件解析
//        filesAppParse.filesParse(param);
//
//        //文件多版本解析(仅文件解析)
//        Integer parseType = param.getParseType();
//        if(!isExtract && (ParseTypeEnums.FILE_PARSE.getCode().equals(parseType) || ParseTypeEnums.FAQ_FILE_PARSE.getCode().equals(parseType)))
//            filesAppParse.fileMultiversionParse(
//                    param.getKnowledgeBaseId(),
//                    param.getFiles().stream().map(FileMessage.File::getFileId).collect(Collectors.toList()),
//                    MultiversionParseEnums.FILENAME_CONTENT,
//                    Arrays.asList(ParseTypeEnums.FILE_PARSE.getCode(),ParseTypeEnums.FAQ_FILE_PARSE.getCode()));
//
//        //FAQ文件抽取
//        if (isExtract)
//            filesAppParse.faqExtract(param);
//
//
//    }
//}
