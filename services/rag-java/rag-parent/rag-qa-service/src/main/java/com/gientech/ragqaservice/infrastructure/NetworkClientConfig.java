package com.gientech.ragqaservice.infrastructure;

import io.netty.channel.ChannelOption;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.context.config.annotation.RefreshScope;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.http.client.reactive.ReactorClientHttpConnector;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.netty.http.client.HttpClient;

import java.time.Duration;

/**
 * @author ws
 * @date 2024年05月31日 6:16 PM
 */
@Configuration
@RefreshScope
public class NetworkClientConfig {
    @Autowired
    public NacosConfig nacosConfig;
    @Bean("restTemplate")
    public RestTemplate restTemplate() {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setReadTimeout(Duration.ofSeconds(1000));//单位为s
        factory.setConnectTimeout(Duration.ofSeconds(100));//单位为s
        return new RestTemplate(factory);
    }

    @Bean("webLlmOpenChatClient")
    public WebClient webLlmOpenChatClient() {
        return  WebClient.builder()
                .clientConnector(
                        new ReactorClientHttpConnector(
                                HttpClient.create()
                                        .option(ChannelOption.CONNECT_TIMEOUT_MILLIS, 100*1000) // 连接超时（单位毫秒）
                                        .responseTimeout(Duration.ofSeconds(1000)) // 响应超时
                        )
                )
                .defaultHeader("Content-Type", "application/json")//设置默认请求类型
                .defaultHeader("accept", "text/event-stream")
                .build();
    }
}
