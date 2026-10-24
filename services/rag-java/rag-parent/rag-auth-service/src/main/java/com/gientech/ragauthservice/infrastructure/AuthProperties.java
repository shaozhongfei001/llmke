package com.gientech.ragauthservice.infrastructure;

import lombok.Data;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.context.config.annotation.RefreshScope;
import org.springframework.context.annotation.Configuration;

@Configuration
@RefreshScope
@Data
public class AuthProperties {

    /**
     * 普通用户角色id
     */
    @Value("${auth.default.role-id}")
    private Long defaultRoleId;

    /**
     * 超级管理员角色id
     */
    @Value("${auth.super.role-id}")
    private Long superRoleId;

    /**
     * 管理员
     */
    @Value("${auth.admin.role-id}")
    private Long adminRoleId;


    @Value("${loginSetting.appKeys}")
    private String appKeys="[]";

}
