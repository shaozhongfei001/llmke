package com.gientech.ragauthservice.interfaces;

import com.gientech.ragauthservice.application.service.AuthenticateAppService;
import com.gientech.ragcommon.context.user.User;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.apache.tika.utils.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.http.ResponseCookie;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.io.IOException;
import java.time.Duration;

@Tag(name = "鉴权相关接口")
@RestController
@RequestMapping("/authenticate")
public class AuthenticateController {

    @Autowired
    private AuthenticateAppService authenticateAppService;

    @Operation(summary = "校验接口是否有权限")
    @GetMapping("")
    public Boolean authenticate(@RequestParam(value = "userName") String userName, @RequestParam("url") String url, @RequestParam("method") String method) {
        return authenticateAppService.authenticate(userName, url, method);
    }

    @Operation(summary = "解码token，获取对应用户信息")
    @GetMapping("/decodeToken")
    public User decodeToken(@RequestParam("token") String token) {
        return authenticateAppService.decodeToken(token);
    }

}
