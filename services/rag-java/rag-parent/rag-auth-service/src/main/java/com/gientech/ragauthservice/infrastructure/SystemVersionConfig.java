package com.gientech.ragauthservice.infrastructure;

import lombok.Data;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.context.config.annotation.RefreshScope;
import org.springframework.context.annotation.Configuration;

/**
 * @Descrption: 系统版本控制
 * @Author:liutaiyun
 * @Date:2024/08/27 14:35
 **/

@Configuration
@RefreshScope
@Data
public class SystemVersionConfig {

    /**
     * 主版本号
     */
    @Value("${system.version}")
    private String version;

    /**
     * 子版本
     */
    @Value("${system.subversion}")
    private String subVersion;

    /**
     * 版本详情（变更内容）
     */
    @Value("${system.detail}")
    private String detail;

    /**
     * 版本创建日期
     */
    @Value("${system.date}")
    private String Date;
}
