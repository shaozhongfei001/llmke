package com.gientech.ragauthservice;

import com.gientech.ragcommon.infrastructure.application.CommmonApplication;
import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;
import org.springframework.cloud.openfeign.EnableFeignClients;

@SpringBootApplication(scanBasePackages = {
        "com.gientech.ragauthservice",
        "com.gientech.ragcommon",
        "com.gitee.sunchenbin.mybatis.actable.manager.*",
        "com.gientech.start.swagger",
        "com.gientech.start.easyexcel",
        "com.gientech.start.redisson",
        "com.gientech.start.storage"
})
@MapperScan(basePackages = {
        "com.gientech.ragauthservice.domain.mapper",
        "com.gientech.ragcommon.operation.mapper",
        "com.gitee.sunchenbin.mybatis.actable.dao.*"
})
@EnableFeignClients
@EnableDiscoveryClient
public class RagAuthServiceApplication {

    public static void main(String[] args) {
        CommmonApplication.run(RagAuthServiceApplication.class, args);
    }
}
