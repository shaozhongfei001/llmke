package com.gientech.ragcommon.auth.authenticate.remote;

import com.gientech.ragcommon.auth.request.SaveInterfaceInfoReq;
import com.gientech.ragcommon.feign.FeignCustomConfig;
import com.gientech.ragcommon.global.CommonResponse;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@FeignClient(name="rag-auth-service",path = "auth/interface",configuration = FeignCustomConfig.class)
public interface InterfaceClient {

    @PostMapping("/saveBatch")
    Boolean saveBatch(@RequestBody List<SaveInterfaceInfoReq> infoReqs);
}
