//package com.gientech.ragcommon.feign;
//
//import org.springframework.boot.web.servlet.FilterRegistrationBean;
//import org.springframework.context.annotation.Bean;
//import org.springframework.context.annotation.Configuration;
//import org.springframework.web.cors.CorsConfiguration;
//import org.springframework.web.cors.UrlBasedCorsConfigurationSource;
//import org.springframework.web.filter.CorsFilter;
//
///**
// * @author ws
// * @date 2024年05月15日 5:41 PM
// */
//@Configuration
//public class CorsConfig {
//
//    @Bean
//    public FilterRegistrationBean crosFilter() {
//        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
//        CorsConfiguration cros = new CorsConfiguration();
//        cros.setAllowCredentials(false);
//        cros.addAllowedOrigin("*");
//        cros.addAllowedHeader("*");
//        cros.addAllowedMethod("*");
//        source.registerCorsConfiguration("/**", cros);
//        FilterRegistrationBean bean = new FilterRegistrationBean(new CorsFilter(source));
//        bean.setOrder(0);
//        return bean;
//    }
//}
