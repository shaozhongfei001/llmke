package com.gientech.raggateway.application.remote;

import com.gientech.ragcommon.feign.FeignCustomConfig;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;

/**
 * @Description:
 * @Author: ws
 * @Date: 2024/5/27 16:19
 */
@FeignClient(name="rag-auth-service", url = "${remote.api.auth.uri:}", path = "auth/authenticate",configuration = FeignCustomConfig.class)
public interface AuthenticateAppService {

    @GetMapping("")
    Boolean authenticate(@RequestParam(value = "userName") String userName, @RequestParam("url")  String url,@RequestParam("method") String method);
}
