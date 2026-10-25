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
        return template -> {
            template.header("X-Feign-Client", "true");
            // R13-SEC-A1：服务间调用必须携带当前主体，否则下游只能按"无主体"处理，
            // 对象级授权会被算成 0（拒绝一切）或误判为管理员（放行一切），两种都不可接受。
            com.gientech.ragcommon.context.user.User current =
                    com.gientech.ragcommon.context.user.UserContext.getUser();
            if (current != null) {
                if (org.apache.commons.lang3.StringUtils.isNotBlank(current.getUserId())) {
                    template.header(com.gientech.ragcommon.global.OpenApiHeader.USER_ID_HEADER, current.getUserId());
                }
                if (org.apache.commons.lang3.StringUtils.isNotBlank(current.getUserName())) {
                    template.header(com.gientech.ragcommon.global.OpenApiHeader.USER_NAME_HEADER, current.getUserName());
                }
                if (org.apache.commons.lang3.StringUtils.isNotBlank(current.getAppKey())) {
                    template.header("appKey", current.getAppKey());
                }
                if (org.apache.commons.lang3.StringUtils.isNotBlank(current.getApiKey())) {
                    template.header("Authorization", current.getApiKey());
                }
            }
        };
    }
}
