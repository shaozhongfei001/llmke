//package com.gientech.ragindexservice.infrastructure;
//
//import lombok.Data;
//import org.springframework.beans.factory.annotation.Value;
//import org.springframework.cloud.context.config.annotation.RefreshScope;
//import org.springframework.stereotype.Component;
//
//@RefreshScope
//@Component
//@Data
//public class KbModelConfig {
//
//    /**
//     * faq润色模型
//     */
//    @Value("${kb.faq-polish-model}")
//    private String faqPolishModel;
//
//    /**
//     * faq相似问模型
//     */
//    @Value("${kb.faq-simiquestion-model}")
//    private String faqSimiQuestionModel;
//
//    /**
//     * faq抽取模型
//     */
//    @Value("${kb.faq-extract-model}")
//    private String faqExtractModel;
//
//    /**
//     * 图解析模型
//     */
//    @Value("${kb.generate-graph-model}")
//    private String generateGraphModel;
//}