package com.gientech.raggateway.application.remote;

import com.gientech.ragcommon.auth.dto.UserInfoDTO;
import com.gientech.ragcommon.feign.FeignCustomConfig;
import com.gientech.ragcommon.global.CommonResponse;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;

@FeignClient(name="rag-auth-service", path = "auth/user" ,configuration = FeignCustomConfig.class)
public interface UserInfoAppService {
    @GetMapping("/getUserInfoByAppKey")
    UserInfoDTO getUserInfoByAppKey(@RequestParam("appKey") String appKey);
}
