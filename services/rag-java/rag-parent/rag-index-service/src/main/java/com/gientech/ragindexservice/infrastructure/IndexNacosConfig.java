package com.gientech.ragindexservice.infrastructure;

import lombok.Getter;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.context.config.annotation.RefreshScope;
import org.springframework.context.annotation.Configuration;

/**
 * @Desc
 * @Author ZhenPanHong
 * @Date 2025/3/5 16:35
 */
@Configuration
@RefreshScope
@Getter
public class IndexNacosConfig {

    @Value("${model.types}")
    private String defaultModelTypes;

    @Value("${model.protocols}")
    private String defaultModelProtocols;
}
