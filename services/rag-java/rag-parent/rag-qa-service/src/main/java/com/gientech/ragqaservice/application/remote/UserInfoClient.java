package com.gientech.ragqaservice.application.remote;

import com.gientech.ragcommon.auth.dto.UserInfoDTO;
import com.gientech.ragcommon.feign.FeignCustomConfig;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;

@FeignClient(name = "rag-auth-service", path = "auth/user",configuration = FeignCustomConfig.class)
public interface UserInfoClient {

    @GetMapping("/getUserInfo")
    UserInfoDTO getUserInfo();

    @GetMapping("/getUserInfoByUserName/{userName}")
    UserInfoDTO getUserInfoByUserName(@PathVariable("userName") String userName);
}
