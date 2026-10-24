package com.gientech.ragqaservice.infrastructure;


import io.swagger.v3.oas.annotations.enums.ParameterIn;
import io.swagger.v3.oas.models.ExternalDocumentation;
import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.Operation;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.media.StringSchema;
import io.swagger.v3.oas.models.parameters.Parameter;
import org.springdoc.core.models.GroupedOpenApi;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.method.HandlerMethod;

@Configuration
public class SpringDocGroupConfiguration {

    @Value("${spring.application.name:}")
    private String applicationName;

    @Bean
    public OpenAPI springShopOpenAPI() {
        return new OpenAPI()
                .info(new Info().title(applicationName + "接口文档").version("v1.0.0"))
                .externalDocs(new ExternalDocumentation().description("rag"));
    }

    @Bean
    public GroupedOpenApi qaApi() {
        return GroupedOpenApi.builder()
                .group("qa")
                .pathsToMatch("/apis/**")
                .addOperationCustomizer((Operation operation, HandlerMethod handlerMethod) ->
                        operation.addParametersItem(new Parameter()
                                .in(ParameterIn.HEADER.toString())
                                .schema(new StringSchema())
                                .name("Authorization")
                                .description("用户token")
                                .required(false))
                )
                .build();
    }

    @Bean
    public GroupedOpenApi publicApi() {
        return GroupedOpenApi.builder()
                .group("all")
                .pathsToMatch("/**")
                .addOperationCustomizer((Operation operation, HandlerMethod handlerMethod) ->
                        operation.addParametersItem(new Parameter()
                                .in(ParameterIn.HEADER.toString())
                                .schema(new StringSchema())
                                .name("Authorization")
                                .description("用户token")
                                .required(false))
                )
                .build();
    }
}
