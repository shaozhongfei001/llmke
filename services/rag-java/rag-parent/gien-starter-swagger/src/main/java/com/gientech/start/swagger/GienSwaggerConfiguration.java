package com.gientech.start.swagger;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.boot.autoconfigure.condition.ConditionalOnClass;
import org.springframework.boot.autoconfigure.condition.ConditionalOnMissingBean;
import org.springframework.context.annotation.Bean;

/** R12 兼容实现：提供最小 OpenAPI 元数据（原内网 starter 仅做 swagger 分组配置）。 */
@AutoConfiguration
@ConditionalOnClass(OpenAPI.class)
public class GienSwaggerConfiguration {

    @Bean
    @ConditionalOnMissingBean(OpenAPI.class)
    public OpenAPI gienOpenAPI() {
        return new OpenAPI().info(new Info().title("LLMKE RAG API").version("r12"));
    }
}
