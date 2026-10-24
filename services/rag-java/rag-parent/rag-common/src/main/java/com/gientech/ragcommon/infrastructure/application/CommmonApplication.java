package com.gientech.ragcommon.infrastructure.application;

import com.gientech.ragcommon.auth.authenticate.InitInterface;
import com.gitee.sunchenbin.mybatis.actable.manager.handler.StartUpHandler;
import org.springframework.boot.SpringApplication;
import org.springframework.context.ConfigurableApplicationContext;

public class CommmonApplication {

    public static void run(Class clazz, String[] args){
        ConfigurableApplicationContext run = SpringApplication.run(clazz, args);
        StartUpHandler bean =run.getBean(StartUpHandler.class, args);
        bean.startHandler();
        //将接口信息同步到数据库中
        InitInterface initInterface = run.getBean(InitInterface.class, args);
        initInterface.init();
    }
}
