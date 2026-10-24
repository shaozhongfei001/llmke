package com.gientech.ragindexservice.application.mq;

import com.alibaba.fastjson2.JSON;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragcommon.index.parameter.FileParseTaskInfo;
import com.gientech.ragcommon.infrastructure.emuns.MessageChannel;
import com.gientech.ragindexservice.application.service.FileAppService;
import lombok.extern.slf4j.Slf4j;
import org.apache.rocketmq.spring.annotation.ConsumeMode;
import org.apache.rocketmq.spring.annotation.MessageModel;
import org.apache.rocketmq.spring.annotation.RocketMQMessageListener;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

/**
 *
 */
@Slf4j
@Component
@RocketMQMessageListener(consumerGroup = MessageChannel.KB_FILE_PARSE_GROUP,
        topic = MessageChannel.KB_FILE_PARSE_TOPIC, messageModel = MessageModel.CLUSTERING,
        consumeMode = ConsumeMode.ORDERLY,consumeThreadNumber = 3,maxReconsumeTimes = 0
)
public class KbFileParseConsume extends AbstarctKbFileConsume {

    @Autowired
    private FileAppService filesAppParse;

    @Override
    protected void dealFile(FileParseTaskInfo param) {
        log.info("收到消息：{}", JSON.toJSONString(param));
        //文件解析(同步的方式)
        filesAppParse.filesParseSync(param);
    }
}
