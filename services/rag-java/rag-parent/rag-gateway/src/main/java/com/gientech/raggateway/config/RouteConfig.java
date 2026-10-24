package com.gientech.raggateway.config;


import com.gientech.raggateway.filter.AuthFilter;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.boot.autoconfigure.http.HttpMessageConverters;
import org.springframework.cloud.gateway.route.RouteLocator;
import org.springframework.cloud.gateway.route.builder.RouteLocatorBuilder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.converter.HttpMessageConverter;

import java.util.stream.Collectors;

/**
 * @Description:
 * @Author: ws
 * @Date: 2024/5/27 16:19
 */
@Configuration
public class RouteConfig {
    @Bean
    public RouteLocator customizeRoute(RouteLocatorBuilder builder, AuthFilter authFilter) {
        return builder.routes()
                .route("auth", r -> r.path("/auth/**").filters(f -> f.filter(authFilter)).uri("lb://rag-auth-service"))
                .route("qa", r -> r.path("/qa/**").filters(f -> f.filter(authFilter)).uri("lb://rag-qa-service"))
                .route("pydemo", r -> r.path("/pydemo/**").filters(f -> f.filter(authFilter)).uri("lb://pydemo"))
                .route("index", r -> r.path("/index/**").filters(f -> f.filter(authFilter)).uri("lb://rag-index-service"))
                .route("dw", r -> r.path("/dw/**").filters(f -> f.filter(authFilter)).uri("lb://intelbrain-dw"))
                .route("sensitive", r -> r.path("/sensitive/**").filters(f -> f.filter(authFilter)).uri("lb://sensitive-words-service"))
                .route("graph", r -> r.path("/graph/**").filters(f -> f.filter(authFilter)).uri("lb://rag-graph-service"))
                .route("aipower", r -> r.path("/aipower/**").filters(f -> f.filter(authFilter)).uri("lb://rag-aipower-service"))
                .build();
    }

    @Bean
    @ConditionalOnMissingBean
    public HttpMessageConverters messageConverters(ObjectProvider<HttpMessageConverter<?>> converters) {
        return new HttpMessageConverters(converters.orderedStream().collect(Collectors.toList()));
    }
}
