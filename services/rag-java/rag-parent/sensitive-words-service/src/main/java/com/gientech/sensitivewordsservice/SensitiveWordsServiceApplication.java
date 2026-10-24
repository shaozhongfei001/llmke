package com.gientech.sensitivewordsservice;

import com.gientech.ragcommon.infrastructure.application.CommmonApplication;
import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.client.discovery.EnableDiscoveryClient;
import org.springframework.cloud.openfeign.EnableFeignClients;

@EnableDiscoveryClient
@EnableFeignClients
@SpringBootApplication(scanBasePackages = {
        "com.gientech.sensitivewordsservice",
        "com.gientech.ragcommon",
        "com.gitee.sunchenbin.mybatis.actable.manager.*",
        "com.gientech.start.swagger",
        "com.gientech.start.redisson"
})
@MapperScan(basePackages = {
        "com.gientech.sensitivewordsservice.domain.mapper",
        "com.gientech.ragcommon.operation.mapper",
        "com.gitee.sunchenbin.mybatis.actable.dao.*"
})
public class SensitiveWordsServiceApplication {

    public static void main(String[] args) {
        CommmonApplication.run(SensitiveWordsServiceApplication.class,args);
    }

}
