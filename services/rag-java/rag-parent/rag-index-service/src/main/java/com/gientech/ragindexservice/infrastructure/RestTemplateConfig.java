package com.gientech.ragindexservice.infrastructure;


import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.context.config.annotation.RefreshScope;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestTemplate;

/**
 * @author chenjuan
 * @date 2025/6/6 14:29
 */
@Configuration
@RefreshScope
public class RestTemplateConfig {
    // 设置连接和读取超时时间（单位：毫秒）
    @Value("${rest-template.connect-timeout:18000000}")
    private int connectTimeout;//5h

    @Value("${rest-template.read-timeout:18000000}")
    private int readTimeout;//5h


    @Bean
    public RestTemplate createRestTemplate() {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(connectTimeout); // 建立连接超时（毫秒）
        factory.setReadTimeout(readTimeout);   // 读取超时（毫秒）

        return new RestTemplate(factory);
//        return new RestTemplate();
    }
}
