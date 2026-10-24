//package com.gientech.ragindexservice.application.mq;
//
//import com.gientech.ragcommon.context.user.User;
//import com.gientech.ragcommon.context.user.UserContext;
//import com.gientech.ragcommon.index.parameter.FileMessage;
//import com.gientech.ragcommon.infrastructure.emuns.MessageChannel;
//import com.gientech.ragindexservice.application.service.FileAppService;
//import lombok.extern.slf4j.Slf4j;
//import org.apache.rocketmq.spring.annotation.MessageModel;
//import org.apache.rocketmq.spring.annotation.RocketMQMessageListener;
//import org.springframework.beans.factory.annotation.Autowired;
//import org.springframework.stereotype.Component;
//
///**
// * 图抽取
// */
//@Slf4j
//@Component
//@RocketMQMessageListener(consumerGroup = MessageChannel.KB_FILE_PARSE_GRAPH_GROUP,
//        topic = MessageChannel.KB_FILE_PARSE_GRAPH_TOPIC, messageModel = MessageModel.CLUSTERING)
//public class KbFileParseGraphConsume extends AbstarctKbFileConsume {
//
//    @Autowired
//    private FileAppService filesAppParse;
//
//    @Override
//    protected void dealFile(FileMessage param) {
//
//        //设置用户上下文信息
//        User user = new User();
//        user.setUserId(param.getUserId());
//        user.setUserName(param.getUserName());
//        UserContext.setUser(user);
//
//        //文件解析
//        filesAppParse.filesParse(param);
//        //图数据生成
//        filesAppParse.generateGraph(param);
//    }
//}
