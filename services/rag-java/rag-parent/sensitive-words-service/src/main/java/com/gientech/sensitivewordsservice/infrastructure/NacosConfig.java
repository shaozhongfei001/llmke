package com.gientech.sensitivewordsservice.infrastructure;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.cloud.context.config.annotation.RefreshScope;
import org.springframework.stereotype.Component;
import java.util.List;

/**
 *  定义一些配置
 */

@Component
@ConfigurationProperties(prefix = "common")
@RefreshScope
@Data
public class NacosConfig {

    /**
     *  默认的敏感词库
     */
    private List<Long> sensitiveWordsId;
}
