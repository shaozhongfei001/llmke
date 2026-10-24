package com.gientech.ragcommon.context.user;

import com.gientech.ragcommon.global.OpenApiHeader;
import com.gientech.ragcommon.infrastructure.utils.JWTUtils;
import com.gientech.ragcommon.qa.constant.QaConstant;
import com.gientech.start.redisson.utils.RedissonUtils;
import feign.RequestInterceptor;
import feign.RequestTemplate;
import jakarta.servlet.http.HttpServletRequest;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import org.springframework.web.context.request.RequestAttributes;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

import java.util.Objects;


@Component
public class FeginTokenRequestInterceptor implements RequestInterceptor {

    @Autowired
    private RedissonUtils redissonUtils;

    @Override
    public void apply(RequestTemplate requestTemplate) {
        RequestAttributes requestAttributes = RequestContextHolder.getRequestAttributes();
        ServletRequestAttributes attributes = (ServletRequestAttributes) requestAttributes;
        User user = UserContext.getUser();
        if(!Objects.isNull(user)){
            String userId = user.getUserId();
            String userName = user.getUserName();
            requestTemplate.header(OpenApiHeader.USER_ID_HEADER, userId);
            requestTemplate.header(OpenApiHeader.USER_NAME_HEADER, userName);
            requestTemplate.header(OpenApiHeader.AUTHORIZATION, user.getApiKey());
            return;
        }
        HttpServletRequest request = attributes.getRequest();
        String userId = null;
        String userName = null;
        String token = request.getHeader("Authorization");
        String appKey = request.getHeader("appKey");

        if (request.getRequestURL().indexOf("/api") > 0 && !request.getRequestURL().toString().contains("apiKey") && !request.getRequestURL().toString().contains("apis")) {
            userId = request.getHeader(OpenApiHeader.USER_ID_HEADER);
            userName = request.getHeader(OpenApiHeader.USER_NAME_HEADER);
            requestTemplate.header(OpenApiHeader.USER_ID_HEADER, userId);
            requestTemplate.header(OpenApiHeader.USER_NAME_HEADER, userName);
        } else {
            if (StringUtils.isNotEmpty(token)) {
                if(token.startsWith(QaConstant.API_KEY_PREFIX))
                    requestTemplate.header("Authorization", token);
                else {
                    userId = JWTUtils.getUserId(token).toString();
                    userName = JWTUtils.getUsername(token);
                }
            } else if (StringUtils.isNotEmpty(appKey)) {
                userId = redissonUtils.get(appKey + ":USER_ID");
                userName = redissonUtils.get(appKey + ":USER_NAME");
            }
        }

        if (StringUtils.isNotBlank(userId) && StringUtils.isNotBlank(userName)) {
            requestTemplate.header("userId", userId);
            requestTemplate.header("userName", userName);
            requestTemplate.header("Authorization", token);
            requestTemplate.header("appKey", appKey);
        }
    }
}