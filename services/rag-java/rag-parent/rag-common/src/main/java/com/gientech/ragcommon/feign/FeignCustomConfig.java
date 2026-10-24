package com.gientech.ragcommon.feign;

import feign.RequestInterceptor;
import org.springframework.context.annotation.Bean;

/**
 * @Description:
 * @Author: chenjuan
 * @Date: 2024/8/29 14:46
 */
public class FeignCustomConfig {
    /**
     * 给feign调用增加自定义请求头，标识是feign调用，如果是则不wrap CommonResponse
     *
     * @return
     */
    @Bean
    public RequestInterceptor requestInterceptor() {
        return template -> template.header("X-Feign-Client", "true");
    }
}
