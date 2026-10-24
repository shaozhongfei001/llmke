package com.gientech.ragcommon.feign;

import feign.RequestInterceptor;
import org.springframework.context.annotation.Bean;

/**
 * @author chenjuan
 * @date 2025/5/21 10:25
 */
public class FeignPythonClientConfig {
    /**
     * 给feign调用增加自定义请求头，标识是feign调用，如果是则不wrap CommonResponse
     *
     * @return
     */
    @Bean
    public RequestInterceptor requestInterceptor() {
        return template -> template.header("X-Python-Label-Client", "true");
    }
}
