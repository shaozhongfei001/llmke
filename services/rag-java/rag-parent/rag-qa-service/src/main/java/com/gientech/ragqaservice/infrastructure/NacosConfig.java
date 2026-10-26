package com.gientech.ragqaservice.infrastructure;

import lombok.Data;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.context.config.annotation.RefreshScope;
import org.springframework.context.annotation.Configuration;

import java.util.List;

/**
 * @author ws
 * @date 2024年06月19日 9:40 AM
 */

@Configuration
@RefreshScope
@Data
public class NacosConfig {

    @Value("${spring.ai.gt.search-docs-url}")
    private String searchDocsUrl;

    /**
     * R13-GRAPH-01：GraphRAG 全局问答入口（社区摘要 map-reduce）。
     * 默认走本地算法服务的 /retrieval_documents_global，可按环境覆盖。
     */
    @Value("${spring.ai.gt.search-docs-global-url:http://127.0.0.1:19995/retrieval_documents_global}")
    private String searchDocsGlobalUrl;

    @Value("${spring.ai.gt.llm-faq-select-url}")
    private String faqSelectUrl;

    @Value("${spring.ai.gt.llm-chat-url}")
    private String llmChatUrl;

    @Value("${spring.ai.gt.llm-open-chat-url}")
    private String llmOpenChatUrl;

    /**
     * 表格问答
     */
    @Value("${spring.ai.gt.llm-rotate-answer}")
    private String llmRotateAnswer;

    @Value("${spring.ai.gt.llm-url}")
    private String llmUrl;

    @Value("${spring.ai.gt.audio-identify-url}")
    private String audioIdentifyUrl;

    @Value("${spring.ai.gt.request-length-limit}")
    private Long requestLengthLimit;

    @Value("${spring.ai.gt.select-model-names}")
    private String selectModelNames;


    @Value("${minio.uri}")
    private String minioUrl;

    @Value("${default.search-conf}")
    private String defaultSearchConf;

    @Value("${spring.ai.gt.llm-question-rewrite-url}")
    private String llmQuestionRewrite;

}
