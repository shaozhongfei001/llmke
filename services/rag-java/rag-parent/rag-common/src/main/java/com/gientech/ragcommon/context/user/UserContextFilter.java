package com.gientech.ragcommon.context.user;

import com.gientech.ragcommon.global.OpenApiHeader;
import com.gientech.ragcommon.infrastructure.utils.JWTUtils;
import com.gientech.ragcommon.qa.constant.QaConstant;
import com.gientech.start.redisson.utils.RedissonUtils;
import jakarta.servlet.*;
import jakarta.servlet.annotation.WebFilter;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;
import org.springframework.web.servlet.mvc.method.annotation.RequestMappingHandlerMapping;

import java.io.IOException;
import java.net.URLDecoder;

@Component
@Order(1)
public class UserContextFilter extends OncePerRequestFilter {

    @Autowired
    private RedissonUtils redissonUtils;


    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain) throws ServletException, IOException {

        //默认从请求头获取数据
        String userId = request.getHeader(OpenApiHeader.USER_ID_HEADER);
        String userName = request.getHeader(OpenApiHeader.USER_NAME_HEADER);
        User user = new User();
        String token = request.getHeader("Authorization");

        String appKey = request.getHeader("appKey");
        if (request.getRequestURL().indexOf("/api") > 0 && !request.getRequestURL().toString().contains("apiKey") && !request.getRequestURL().toString().contains("apis")) {
            userId = request.getHeader(OpenApiHeader.USER_ID_HEADER);
            userName = request.getHeader(OpenApiHeader.USER_NAME_HEADER);
        } else {
            if(StringUtils.isNotEmpty(token) && token.startsWith(QaConstant.API_KEY_PREFIX)){
                userId = "-1";
                user.setApiKey(token);
            } else if (StringUtils.isNotEmpty(token) && !token.startsWith(QaConstant.API_KEY_PREFIX)) {
                userId = JWTUtils.getUserId(token).toString();
                userName = JWTUtils.getUsername(token);
            } else if (StringUtils.isNotEmpty(appKey)) {
                userId = redissonUtils.get(appKey + ":USER_ID");
                userName = redissonUtils.get(appKey + ":USER_NAME");
            }
        }

        user.setAppKey(appKey);
        user.setUserId(userId);
        user.setUserName(StringUtils.isNotBlank(userName) ? URLDecoder.decode(userName, "UTF-8") : null);
        UserContext.setUser(user);
        filterChain.doFilter(request, response);
    }
}
