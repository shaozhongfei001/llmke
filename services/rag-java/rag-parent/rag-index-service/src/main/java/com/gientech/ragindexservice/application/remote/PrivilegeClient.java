package com.gientech.ragindexservice.application.remote;

import com.gientech.ragcommon.auth.dto.PrivilegeDTO;
import com.gientech.ragcommon.feign.FeignCustomConfig;
import com.gientech.ragcommon.global.CommonResponse;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;

import java.util.List;
import java.util.Map;

@FeignClient(name = "rag-auth-service", path = "auth/privilege",configuration = FeignCustomConfig.class)
public interface PrivilegeClient {

    @GetMapping("/getPermission")
    Map<Long, PrivilegeDTO> getPermission(@RequestParam(value = "bizType", defaultValue = "1") Integer bizType, @RequestParam(value = "userName", required = false) String userName);

    @GetMapping("/api/isPermission")
    Boolean isPermissionApi(@RequestParam(value = "bizType",defaultValue = "1") Integer bizType,@RequestParam("targetId") Long targetId);

    @GetMapping("/getAllPermission")
    List<PrivilegeDTO> getAllPermission(@RequestParam(value = "bizType") Integer bizType, @RequestParam(value = "userName", required = false) String userName);
}
