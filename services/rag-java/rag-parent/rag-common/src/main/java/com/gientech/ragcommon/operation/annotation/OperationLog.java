package com.gientech.ragcommon.operation.annotation;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

/**
 * @Descrption:
 * @Author:liutaiyun
 * @Date:2024/12/24 11:00
 **/
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface OperationLog {
    String operateType() default "用户操作";
}
