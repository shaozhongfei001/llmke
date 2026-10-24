package com.gientech.start.easyexcel.utils;

import org.springframework.beans.BeansException;
import org.springframework.context.ApplicationContext;
import org.springframework.context.ApplicationContextAware;
import org.springframework.stereotype.Component;

/** Spring 上下文静态访问（R12 兼容实现）。 */
@Component
public class SpringContextUtil implements ApplicationContextAware {

    private static ApplicationContext context;

    @Override
    public void setApplicationContext(ApplicationContext applicationContext) throws BeansException {
        SpringContextUtil.context = applicationContext;
    }

    public static <T> T getBean(Class<T> clazz) {
        if (context == null) {
            throw new IllegalStateException("ApplicationContext 尚未初始化");
        }
        return context.getBean(clazz);
    }

    public static Object getBean(String name) {
        if (context == null) {
            throw new IllegalStateException("ApplicationContext 尚未初始化");
        }
        return context.getBean(name);
    }
}
