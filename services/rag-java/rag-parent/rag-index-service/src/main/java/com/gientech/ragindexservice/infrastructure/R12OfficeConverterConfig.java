package com.gientech.ragindexservice.infrastructure;

import org.jodconverter.core.DocumentConverter;
import org.jodconverter.core.office.OfficeManager;
import org.jodconverter.local.LocalConverter;
import org.jodconverter.local.office.LocalOfficeManager;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * R12-ADAPT A-07：文档转换（LibreOffice）装配。
 * <p>
 * 背景：原内网依赖 jodconverter-spring-boot-starter 的自动装配，但该 starter 4.4.x 使用的是
 * Boot 2 的 spring.factories 机制，在 Spring Boot 3.2 下不会被加载，导致
 * {@code @Autowired DocumentConverter} 无 Bean（启动失败）。
 * 处理：显式装配 LocalOfficeManager + LocalConverter，语义与 starter 默认一致（本地 soffice）。
 * 影响面：仅 doc/docx/ppt 转 PDF 预览通路；不影响解析与检索主链。
 */
@Configuration
public class R12OfficeConverterConfig {

    @Bean(initMethod = "start", destroyMethod = "stop")
    public OfficeManager r12OfficeManager(
            @Value("${jodconverter.local.office-home:/usr/lib/libreoffice}") String officeHome,
            @Value("${jodconverter.local.port-numbers:2002}") int port) {
        return LocalOfficeManager.builder()
                .officeHome(officeHome)
                .portNumbers(port)
                .taskExecutionTimeout(180_000L)
                .processTimeout(240_000L)
                .build();
    }

    @Bean
    public DocumentConverter documentConverter(OfficeManager r12OfficeManager) {
        return LocalConverter.builder().officeManager(r12OfficeManager).build();
    }
}
