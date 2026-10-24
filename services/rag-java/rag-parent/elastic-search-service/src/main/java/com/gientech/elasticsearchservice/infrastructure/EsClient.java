package com.gientech.elasticsearchservice.infrastructure;

import co.elastic.clients.elasticsearch.ElasticsearchClient;
import co.elastic.clients.json.jackson.JacksonJsonpMapper;
import co.elastic.clients.transport.ElasticsearchTransport;
import co.elastic.clients.transport.rest_client.RestClientTransport;
import jakarta.annotation.PreDestroy;
import org.apache.http.Header;
import org.apache.http.HttpHost;
import org.apache.http.message.BasicHeader;
import org.elasticsearch.client.RestClient;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.io.IOException;

/**
 * @Description:
 * @Author: chenjuan
 * @Date: 2024/9/20 13:46
 */
@Configuration
public class EsClient {

    @Value("${es.api-key:RVRGVENwSUJqWGxac0plalZrZE46QXRtdWk1ZUNSZnFqMHJRVHNVaE16QQ==}")
    private String apiKey;

    @Value("${es.serverUrl:localhost:9200}")
    private String serverUrl;

    @Bean
    public RestClient restClient(){
        return RestClient
                .builder(HttpHost.create(serverUrl))
                .setDefaultHeaders(new Header[]{
                        new BasicHeader("Authorization", "ApiKey " + apiKey)
                })
                .build();
    }

    @Bean
    public ElasticsearchTransport elasticSearchTransport (RestClient restClient) {
        return new RestClientTransport(
                restClient, new JacksonJsonpMapper());
    }
    @Bean
    public ElasticsearchClient getEsClient(ElasticsearchTransport transport){
        return new ElasticsearchClient(transport);
    }
}
