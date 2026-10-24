package com.gientech.raggraphservice;

import com.gientech.ragcommon.auth.authenticate.InitInterface;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.openfeign.EnableFeignClients;
import org.springframework.context.ConfigurableApplicationContext;

@SpringBootApplication(scanBasePackages = {
        "com.gientech.raggraphservice",
        "com.gientech.ragcommon.auth.authenticate",
        "com.gientech.ragcommon.global",
        "com.gientech.start.redisson",
        "com.gientech.ragcommon.context",
        "com.gientech.start.swagger"
})
@EnableFeignClients
public class RagGraphServiceApplication {

    public static void main(String[] args) {
        ConfigurableApplicationContext run = SpringApplication.run(RagGraphServiceApplication.class, args);
        //将接口信息同步到数据库中
        InitInterface initInterface = run.getBean(InitInterface.class, args);
        initInterface.init();
    }

}
