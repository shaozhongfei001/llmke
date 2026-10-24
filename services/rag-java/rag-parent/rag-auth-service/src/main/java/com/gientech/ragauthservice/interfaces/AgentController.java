package com.gientech.ragauthservice.interfaces;


import com.alibaba.fastjson.JSON;
import com.gientech.ragauthservice.application.service.UserInfoAppService;
import com.gientech.ragauthservice.infrastructure.AuthProperties;
import com.gientech.ragcommon.auth.dto.UserInfoDTO;
import com.gientech.ragcommon.auth.request.AgentLoginReq;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.ragcommon.operation.annotation.OperationLog;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cloud.context.config.annotation.RefreshScope;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * <p>
 * 用户表 前端控制器
 * </p>
 *
 * @author ws
 * @since 2025-06-24
 */
@Tag(name = "第三方登录单点登录")
@RestController
@RequestMapping("/agent")
@RefreshScope
public class AgentController {


    @Autowired
    private UserInfoAppService userInfoAppService;

    @Autowired
    private AuthProperties authProperties;

    @Operation(summary = "agent登录")
    @PostMapping("/agentLogin")
    @OperationLog(operateType = "agent登录")
    public UserInfoDTO agentLogin(@RequestBody @Validated AgentLoginReq agentLoginReq,@RequestHeader("app-key") String appKey) {
        if(StringUtils.isEmpty(appKey)){
            throw new ApplicationException(ErrCodeEnum.APP_KEY_NOT_NULL);
        }
        String appKeys = authProperties.getAppKeys();
        List<Map> mapList = JSON.parseArray(appKeys, Map.class);
        Map<String,String> mapKeys = new HashMap<>();
        for(Map map:mapList){
            mapKeys.put(String.valueOf(map.get("appkey")),String.valueOf(map.get("role-id")));
        }
        String roleId = mapKeys.get(appKey);
        if(StringUtils.isEmpty(roleId)){
            throw new ApplicationException(ErrCodeEnum.APP_KEY_NOT_EXIST);
        }
        return userInfoAppService.agentLogin(agentLoginReq,Long.valueOf(roleId));
    }


}
