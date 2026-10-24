package com.gientech.ragindexservice;

import com.gientech.ragcommon.infrastructure.application.CommmonApplication;
import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.openfeign.EnableFeignClients;
import org.springframework.retry.annotation.EnableRetry;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication(scanBasePackages = {
        "com.gientech.ragindexservice",
        "com.gientech.ragcommon",
        "com.gientech.tools",
        "com.gitee.sunchenbin.mybatis.actable.manager.*",
        "com.gientech.start.swagger",
        "com.gientech.start.storage",
        "com.gientech.start.redisson"})
@MapperScan(basePackages = {
        "com.gientech.ragindexservice.domain.mapper",
        "com.gitee.sunchenbin.mybatis.actable.dao.*",
        "com.gientech.ragcommon.operation.mapper",
        "com.gientech.tools.database.domain.mapper"
})
@EnableScheduling
@EnableFeignClients(basePackages = {
        "com.gientech.ragindexservice",
        "com.gientech.tools",
})
@EnableRetry
public class RagIndexServiceApplication {

    public static void main(String[] args) {
        CommmonApplication.run(RagIndexServiceApplication.class,args);
    }

}
