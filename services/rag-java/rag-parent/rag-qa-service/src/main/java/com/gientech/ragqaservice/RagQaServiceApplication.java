package com.gientech.ragqaservice;

import com.gientech.ragcommon.infrastructure.application.CommmonApplication;
import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.openfeign.EnableFeignClients;

@EnableFeignClients
@SpringBootApplication(scanBasePackages = {
        "com.gientech.ragqaservice",
        "com.gientech.ragcommon",
        "com.gitee.sunchenbin.mybatis.actable.manager.*",
//        "com.gientech.start.swagger",
        "com.gientech.start.easyexcel",
        "com.gientech.start.storage",
        "com.gientech.start.redisson"
})
@MapperScan(basePackages = {
        "com.gientech.ragqaservice.domain.mapper",
        "com.gitee.sunchenbin.mybatis.actable.dao.*",
        "com.gientech.ragcommon.operation.mapper"
})
public class RagQaServiceApplication {

    public static void main(String[] args) {
        CommmonApplication.run(RagQaServiceApplication.class,args);
    }

}
