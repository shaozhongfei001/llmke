package com.gientech.ragauthservice.application.service.impl;

import com.alibaba.fastjson2.JSON;
import com.gientech.ragauthservice.application.service.AuthenticateAppService;
import com.gientech.ragauthservice.domain.entity.InterfaceInfo;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.ragcommon.infrastructure.utils.JWTUtils;
import com.gientech.start.redisson.utils.RedissonUtils;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.server.PathContainer;
import org.springframework.stereotype.Service;
import org.springframework.web.util.pattern.PathPattern;
import org.springframework.web.util.pattern.PathPatternParser;

import java.util.regex.Matcher;
import java.util.regex.Pattern;
import java.util.regex.PatternSyntaxException;

import static com.gientech.ragcommon.infrastructure.emuns.RedisKeyEnums.AUTH_USER_RESOURCE;

@Service
@Slf4j
public class AuthenticateAppServiceImpl implements AuthenticateAppService {

    @Autowired
    private RedissonUtils redissonUtils;

    @Override
    public Boolean authenticate(String userName, String url, String method) {
        //未登录
        if (StringUtils.isEmpty(userName)) {
            throw new ApplicationException(ErrCodeEnum.HAS_NOT_LOGIN);
        }
        //该用户是否有权访问
        String appName = url.substring(1, url.indexOf("/", 1));
        String resourcesJson = redissonUtils.hashGet(AUTH_USER_RESOURCE + userName, appName);

        if (StringUtils.isNotBlank(resourcesJson))
            return JSON.parseArray(resourcesJson, InterfaceInfo.class)
                    .stream()
                    .anyMatch(interfaceInfo -> authenticateUrl(interfaceInfo, url, method));
        return false;
    }

    @Override
    public User decodeToken(String token) {
        User user = null;
        try {
            String userId = JWTUtils.getUserId(token).toString();
            String userName = JWTUtils.getUsername(token);
            user = new User();
            user.setUserId(userId);
            user.setUserName(userName);
        } catch (Exception ex) {
            log.error(ex.getMessage(), ex);
        }
        return user;
    }

    private boolean authenticateUrl(InterfaceInfo interfaceInfo, String sourceUrl, String method) {
        String targetUrl = interfaceInfo.getUrl();
        String targetMethod = interfaceInfo.getMethod();
        if (method.equals(targetMethod)) {
            if (!targetUrl.contains("{") && !targetUrl.contains("}") && !sourceUrl.contains("{") && !sourceUrl.contains("}"))
                return sourceUrl.equals(targetUrl);
            return isPathMatch(sourceUrl,targetUrl);
        }
        return false;
    }

    private boolean isPathMatch(String sourceUrl, String targetUrl) {
        //普通匹配
        PathPattern pattern = PathPatternParser.defaultInstance.parse(targetUrl);
        if (pattern.matches(PathContainer.parsePath(sourceUrl))) {
            return true;
        }
        //正则匹配
        try {
            //前段匹配
            PathPattern pathBeforeLastPattern = PathPatternParser.defaultInstance.parse(getPathBeforeLastSegment(targetUrl));
            if (pathBeforeLastPattern.matches(PathContainer.parsePath(getPathBeforeLastSegment(sourceUrl)))) {
                Matcher matcher = Pattern.compile(getLastSegment(targetUrl)).matcher(getLastSegment(getLastSegment(sourceUrl)));
                //最后一段正则匹配
                return matcher.matches();
            }
        } catch (PatternSyntaxException e) {
            return pattern.matches(PathContainer.parsePath(sourceUrl));
        }
        return false;
    }

    private String getLastSegment(String targetUrl) {
        String[] segments = targetUrl.split("/");
        return segments.length > 0 ? segments[segments.length - 1] : "";
    }

    private String getPathBeforeLastSegment(String targetUrl) {
        int index = targetUrl.lastIndexOf("/");
        return index > 0 ? targetUrl.substring(0, index) : "";
    }
}
