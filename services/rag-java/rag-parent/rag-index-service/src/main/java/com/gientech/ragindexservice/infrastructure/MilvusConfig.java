package com.gientech.ragindexservice.infrastructure;

import io.milvus.client.MilvusServiceClient;
import io.milvus.param.ConnectParam;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.stereotype.Component;

/**
 * @Descrption:
 * @Author:liutaiyun Milvus向量数据库Client
 * @Date:2024/08/01 16:18
 **/
@Slf4j
//@Component
public class MilvusConfig {
    @Value("${milvus.host:}")
    private String host; //milvus所在服务器地址
    @Value("${milvus.port}")
    private Integer port; //milvus端口

    @Bean
    public MilvusServiceClient milvusServiceClient() {
        ConnectParam connectParam = ConnectParam.newBuilder()
                .withHost(host)
                .withPort(port)
                .build();
        return new MilvusServiceClient(connectParam);
    }
}
