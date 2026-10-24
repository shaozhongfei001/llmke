package com.gientech.ragcommon.auth.request;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

/**
 * 登录请求
 */
@Data
public class AgentLoginReq {

    @NotBlank(message = "用户名不能为空")
    private String userName;


}
