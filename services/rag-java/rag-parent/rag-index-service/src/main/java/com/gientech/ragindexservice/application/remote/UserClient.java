package com.gientech.ragindexservice.application.remote;

import com.gientech.ragcommon.auth.dto.UserInfoDTO;
import com.gientech.ragcommon.feign.FeignCustomConfig;
import com.gientech.ragcommon.global.CommonResponse;
import com.gientech.ragcommon.operation.annotation.OperationLog;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestParam;

@FeignClient(name="rag-auth-service",path = "auth/user",configuration = FeignCustomConfig.class)
public interface UserClient {

    /**
     * 用户类型 1 超级管理员，null其他用户
     * @return
     */
    @GetMapping("/getUserType")
    Integer getUserType();

    @GetMapping("/getUserInfo")
    UserInfoDTO getUserInfo();

    @GetMapping("/getUserTypeByUserName")
    Integer getUserTypeByUserName(@RequestParam(value = "userName", required = false) String userName);


    @GetMapping("/getUserInfoByUserName/{userName}")
    UserInfoDTO getUserInfoByUserName(@PathVariable("userName") String userName);
}
