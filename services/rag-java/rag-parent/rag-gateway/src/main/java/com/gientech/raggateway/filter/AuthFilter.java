package com.gientech.raggateway.filter;


import com.alibaba.fastjson2.JSON;
import com.gientech.ragcommon.auth.dto.UserInfoDTO;
import com.gientech.ragcommon.auth.enums.UserSysSourceEnums;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragcommon.qa.constant.QaConstant;
import com.gientech.ragcommon.infrastructure.emuns.RedisKeyEnums;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.global.CommonResponse;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.infrastructure.utils.JWTUtils;
import com.gientech.raggateway.application.remote.ApiKeyAppService;
import com.gientech.raggateway.application.remote.AuthenticateAppService;
import com.gientech.raggateway.application.remote.UserInfoAppService;
import com.gientech.start.redisson.utils.RedissonUtils;
import com.google.common.collect.Sets;
import org.springframework.beans.factory.annotation.Value;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.apache.http.HttpHeaders;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cloud.context.config.annotation.RefreshScope;
import org.springframework.cloud.gateway.filter.GatewayFilter;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.context.annotation.Lazy;
import org.springframework.core.Ordered;
import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.http.HttpStatus;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.http.server.reactive.ServerHttpRequestDecorator;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.nio.charset.StandardCharsets;
import java.time.LocalDate;
import java.time.Month;
import java.util.ArrayList;
import java.util.Set;
import java.util.concurrent.TimeUnit;

/**
 * @Description:
 * @Author: ws
 * @Date: 2024/5/27 16:19
 */
@Component
@Slf4j
@RefreshScope
public class AuthFilter implements GatewayFilter, Ordered {

    /**
     * token的有效期
     */
    public static final long DEFAULT_EXPIRE = 60 * 60 * 2;

    @Value("${auth-filter.admin-expire:0}")
    private long adminExpireTime;

    @Value("${auth-filter.no-verify-token:}")
    private String noVerifyToken;

    @Autowired
    private RedissonUtils redissonUtils;

    private AuthenticateAppService authenticateAppService;

    private UserInfoAppService userInfoAppService;

    private ApiKeyAppService apiKeyAppService;

    //无需登录、无需鉴权
    private final Set<String> noTokenPaths = Sets.newHashSet(
            "/auth/user/login",
            "/auth/user/kaptcha",
            "/auth/user/registerKaptcha",
            "/auth/user/regist",
            "/index/knowledgeBase/file/uploadParsedFile",
            "/index/knowledgeBase/file/list",
            "/graph/search/ping",
            "/auth/user/simpleLogin",
            "/index/knowledgeBase/file/multiple/version",
            "/auth/authenticate/callback",
            "/index/parseTask/callback",
            "/auth/agent/agentLogin",
            "/auth/kaptcha/kaptchaSix",
            "/auth/userSecurityQuestion/findByUserName",
            "/auth/userSecurityQuestion/validateSecurityQuestion",
            "/auth/userSecurityQuestion/updatePasswordByQuestion"
    );

    //需要登录才能访问,不需要鉴权
    private final Set<String> noAuthPaths = Sets.newHashSet(
            "/auth/resource/getMenusByUser",
            "/auth/resource/getMenus",
            "/auth/user/logout",
            "/auth/user/getUserType"
    );

    // 产品试用截止日期
    private static final LocalDate EXPIRE_DATE = LocalDate.of(2026, Month.APRIL, 30);

    @Override
    public int getOrder() {
        return 0;
    }

    @Autowired
    public AuthFilter(
            @Lazy AuthenticateAppService authenticateAppService,
            @Lazy UserInfoAppService userInfoAppService,
            @Lazy ApiKeyAppService apiKeyAppService
    ) {
        this.authenticateAppService = authenticateAppService;
        this.userInfoAppService = userInfoAppService;
        this.apiKeyAppService = apiKeyAppService;
    }

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        ServerHttpRequest request = exchange.getRequest();
        ServerHttpResponse response = exchange.getResponse();

//        //给华侨银行POC使用，控制接口使用时间。默认到2026年4月30日
//        if (LocalDate.now().isAfter(EXPIRE_DATE)) {
//            return response(response, HttpStatus.UNAUTHORIZED, ErrCodeEnum.TRIAL_DATE_EXPIRED);
//        }

        String method = request.getMethod().name();
        String path = request.getPath().toString();
        String token = request.getHeaders().getFirst(HttpHeaders.AUTHORIZATION);
        String appKey = request.getHeaders().getFirst("appKey");
        log.info("网关鉴权开始 path:{}", path);
        // 请求头token中包含apiKey前缀，优先验证并且接口放行
        if(StringUtils.isNotBlank(token) && token.startsWith(QaConstant.API_KEY_PREFIX)){
            String apiKey = token;
            if(!apiKeyAppService.checkApiKey(apiKey)){
                log.error("apiKey:{} is not legitimate",apiKey);
                return response(response, HttpStatus.UNAUTHORIZED, ErrCodeEnum.UNAUTHORIZED);
            }else {
                User user = new User();
                user.setApiKey(apiKey);
                UserContext.setUser(user);
            }
        } else if (StringUtils.isNotBlank(appKey)) {
            // 其次请求头包含appKey时，优先对appKey认证
            UserInfoDTO userInfoDTO = userInfoAppService.getUserInfoByAppKey(appKey);
            if (userInfoDTO == null) {
                log.error("appKey is {}, userInfoDTO is null",appKey);
                return response(response, HttpStatus.UNAUTHORIZED, ErrCodeEnum.UNAUTHORIZED);
            } else {
                User user = new User();
                user.setUserName(userInfoDTO.getUserName());
                user.setUserId(String.valueOf(userInfoDTO.getId()));
                user.setAppKey(appKey);
                Integer systemSource = userInfoDTO.getSystemSource();
                if (!UserSysSourceEnums.AGENT.getCode().equals(systemSource) && !isNoAuthFree(path) && !authenticateAppService.authenticate(user.getUserName(), path ,method)) {
                    log.error("appKey is {}, user is {} , but {} no permission",appKey, user.getUserName(), path);
                    return response(response, HttpStatus.UNAUTHORIZED, ErrCodeEnum.UNAUTHORIZED);
                }
                // 刷新用户Redis信息
                refreshUserInfoToRedis(user.getUserName());
                exchange = addUserInfoToHeader(exchange, request, user, token);
            }
        } else {
            if (StringUtils.isNotBlank(noVerifyToken) && noVerifyToken.equals(token)) {
                User user = new User();
                user.setUserName(JWTUtils.getUsername(token));
                user.setUserId(String.valueOf(JWTUtils.getUserId(token)));
                exchange = addUserInfoToHeader(exchange, request, user, token);
            } else if (!isNoTokenFree(path)) {
                if (!StringUtils.isNotBlank(token)) {
                    return response(response, HttpStatus.UNAUTHORIZED, ErrCodeEnum.NO_TOKEN);
                }
                String cacheToken = redissonUtils.get(RedisKeyEnums.USER_TOKEN_PREFIX + JWTUtils.getUsername(token));
                if (StringUtils.isEmpty(cacheToken)) {
                    return response(response, HttpStatus.UNAUTHORIZED, ErrCodeEnum.LOGIN_EXPIRE);
                } else if (!token.equals(cacheToken)) {
                    return response(response, HttpStatus.UNAUTHORIZED, ErrCodeEnum.LOGIN_EXPIRE);
                }
                //获取用户信息并将token续期
                User user = getUserAndRenewal(token);
                if (!isNoAuthFree(path) && !authenticateAppService.authenticate(user.getUserName(), path,method)) {
                    log.error("user is {}-{}, but {}:{} no permission", user.getUserId(),user.getUserName(), method,path);
                    return response(response, HttpStatus.UNAUTHORIZED, ErrCodeEnum.UNAUTHORIZED);
                }
                exchange = addUserInfoToHeader(exchange, request, user, token);
            }
        }
        ServerWebExchange finalExchange = exchange;
        return chain.filter(exchange).then(Mono.defer(() -> {
            finalExchange.getResponse().getHeaders().entrySet().stream()
                    .filter(kv -> (kv.getValue() != null && kv.getValue().size() > 1))
                    .filter(kv -> (kv.getKey().equals(org.springframework.http.HttpHeaders.ACCESS_CONTROL_ALLOW_ORIGIN)
                            || kv.getKey().equals(org.springframework.http.HttpHeaders.ACCESS_CONTROL_ALLOW_CREDENTIALS)))
                    .forEach(kv -> {
                        kv.setValue(new ArrayList<String>() {{
                            add(kv.getValue().get(0));
                        }});
                    });

            return chain.filter(finalExchange);
        }));
    }

    private Mono<Void> response(ServerHttpResponse response, HttpStatus httpStatus, ErrCodeEnum errCodeEnum) {
        log.error("网关鉴权失败："+errCodeEnum.getErrMsg());
        response.setStatusCode(httpStatus);
        response.getHeaders().add("Content-Type", "application/json;charset=UTF-8");
        CommonResponse commonResponse = CommonResponse.fail(errCodeEnum);
        DataBuffer bodyDataBuffer = response.bufferFactory().wrap(JSON.toJSONString(commonResponse).getBytes(StandardCharsets.UTF_8));
        return response.writeWith(Mono.just(bodyDataBuffer));
    }

    private boolean isNoTokenFree(String path) {
        //swager接口放行
        if (path.contains("swagger") || path.contains("/v3/api-docs"))
            return true;
        for (String prefix : noTokenPaths) {
            if (path.startsWith(prefix)) {
                return true;
            }
        }
        return false;
    }

    private boolean isNoAuthFree(String path) {
        for (String prefix : noAuthPaths) {
            if (path.startsWith(prefix)) {
                return true;
            }
        }
        return false;
    }

    private User getUserAndRenewal(String token) {
        String username = JWTUtils.getUsername(token);
        //token续期
        redissonUtils.expireKey(RedisKeyEnums.USER_TOKEN_PREFIX + username, DEFAULT_EXPIRE, TimeUnit.SECONDS);
        redissonUtils.expireKey(RedisKeyEnums.AUTH_USER_RESOURCE + username, DEFAULT_EXPIRE, TimeUnit.SECONDS);
        redissonUtils.expireKey(RedisKeyEnums.AUTH_USER_MENU + username, DEFAULT_EXPIRE, TimeUnit.SECONDS);
        return new User(String.valueOf(JWTUtils.getUserId(token)), JWTUtils.getUsername(token), null,null);
    }

    private void refreshUserInfoToRedis(String userName) {
        redissonUtils.expireKey(RedisKeyEnums.AUTH_USER_RESOURCE + userName, DEFAULT_EXPIRE, TimeUnit.SECONDS);
        redissonUtils.expireKey(RedisKeyEnums.AUTH_USER_MENU + userName, DEFAULT_EXPIRE, TimeUnit.SECONDS);
    }

    private ServerWebExchange addUserInfoToHeader(ServerWebExchange exchange, ServerHttpRequest request, User user, String token) {
        ModifiedServerHttpRequest modifiedRequest = new ModifiedServerHttpRequest(request);
//        modifiedRequest.getHeaders().add("userId", user.getUserId());
//        modifiedRequest.getHeaders().add("userName", user.getUserName());
        modifiedRequest.getHeaders().add("appKey", user.getAppKey());
        modifiedRequest.getHeaders().add("Authorization", token);
        log.info("网关鉴权完成，将用户信息传递到下游: userId:{},userName:{},appKey:{}", user.getUserId(), user.getUserName(), user.getAppKey());
        return exchange.mutate().request(modifiedRequest).build();
    }

    private class ModifiedServerHttpRequest extends ServerHttpRequestDecorator {

        private final org.springframework.http.HttpHeaders headers = new org.springframework.http.HttpHeaders();

        public ModifiedServerHttpRequest(ServerHttpRequest delegate) {
            super(delegate);
            headers.addAll(super.getHeaders());
        }

        @Override
        public org.springframework.http.HttpHeaders getHeaders() {
            return headers;
        }

    }
}
