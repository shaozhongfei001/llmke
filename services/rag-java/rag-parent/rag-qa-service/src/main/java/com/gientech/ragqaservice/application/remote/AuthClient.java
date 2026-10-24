package com.gientech.ragqaservice.application.remote;

import com.gientech.ragcommon.auth.dto.PrivilegeDTO;
import com.gientech.ragcommon.auth.dto.UserInfoDTO;
import com.gientech.ragcommon.feign.FeignCustomConfig;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;

import java.util.List;
import java.util.Map;

@FeignClient(name = "rag-auth-service", path = "auth", configuration = FeignCustomConfig.class)
public interface AuthClient {

    @GetMapping("/privilege/getPermission")
    Map<Long, PrivilegeDTO> getPermission(@RequestParam(value = "bizType", defaultValue = "1") Integer bizType);

    @GetMapping("/privilege/isPermission")
    Boolean isPermission(@RequestParam(value = "bizType", defaultValue = "1") Integer bizType, @RequestParam("targetId") Long targetId);

    @GetMapping("/privilege/getAllPermission")
    List<PrivilegeDTO> getAllPermission(@RequestParam(value = "bizType") Integer bizType, @RequestParam(value = "userName", required = false) String userName);

    @GetMapping("/user/getUserInfo")
    UserInfoDTO getUserInfo();
}
