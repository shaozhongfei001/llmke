package com.gientech.ragcommon.context.user;

import com.gientech.ragcommon.global.OpenApiHeader;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.apache.commons.lang3.StringUtils;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;

/**
 * @author chenjuan
 * @date 2025/2/21 11:43
 */
@Component
@Order(2)
public class OpenApiFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain) throws ServletException, IOException {
        if (request.getRequestURL().indexOf("/api") > 0 && !request.getRequestURL().toString().contains("apiKey") && !request.getRequestURL().toString().contains("apis")) {
            User user = new User();

            String userId = request.getHeader(OpenApiHeader.USER_ID_HEADER);
            String userName = request.getHeader(OpenApiHeader.USER_NAME_HEADER);

            user.setUserId(userId);
            user.setUserName(StringUtils.isNotBlank(userName) ? URLDecoder.decode(userName, StandardCharsets.UTF_8) : null);
            UserContext.setUser(user);
        }
        filterChain.doFilter(request, response);
    }
}
