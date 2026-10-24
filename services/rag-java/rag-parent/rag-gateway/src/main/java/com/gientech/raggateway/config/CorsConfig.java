//package com.gientech.raggateway.config;
//
//import org.springframework.context.annotation.Configuration;
//import org.springframework.web.servlet.config.annotation.CorsRegistry;
//import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;
//
//@Configuration
//public class CorsConfig implements WebMvcConfigurer {
//
//    @Override
//    public void addCorsMappings(CorsRegistry registry) {
//        registry.addMapping("/**") // 匹配所有的URL
//                .allowedOriginPatterns("*") // 允许的域名，生产环境中应指定具体域名
//                .allowedMethods("GET", "POST", "PUT", "DELETE", "OPTIONS") // 允许的HTTP方法
//                .allowedHeaders("*") // 允许的请求头
//                .allowCredentials(true) // 允许携带凭证（如cookie）
//                .maxAge(3600); // 预检请求的有效期（秒）
//    }
//}