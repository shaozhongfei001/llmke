package com.gientech.ragindexservice.application.mq;

import org.apache.rocketmq.client.exception.MQBrokerException;
import org.apache.rocketmq.client.exception.MQClientException;
import com.gientech.ragindexservice.RagIndexServiceApplication;
import com.gientech.ragindexservice.application.service.ModelInfoAppService;
import org.apache.rocketmq.client.producer.DefaultMQProducer;
import org.apache.rocketmq.remoting.exception.RemotingException;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

/**
 * @author: shirleychen
 * @date 2025/11/21 16:38
 * @description
 */
@SpringBootTest(classes = RagIndexServiceApplication.class)
public class ReEmbeddingConsumeTest {
    @Autowired
    private DefaultMQProducer producer;
    @Autowired
    private ModelInfoAppService modelInfoAppService;
    @Test
    public void reEmbeddingTest() throws MQBrokerException, RemotingException, InterruptedException, MQClientException {

    }
}
