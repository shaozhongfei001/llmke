package com.gientech.ragcommon.index.constant;

public interface KbConfigConstant {

    /* ====================文件解析配置===============  */

    /**
     * 最大分段长度
     */
    String CHUNK_SIZE = "chunkSize";

    /**
     * 分段标识符
     */
    String SPLIT_REGEX = "splitRegex";

    /**
     * 分段重叠长度
     */
    String CHUNK_OVERLAP = "chunkOverlap";

    /**
     * 文件解析方式
     */
    String FILE_TYPE = "fileType";

    /**
     * 嵌入模型
     */
    String EMBEDDING_MODEL_NAME = "embeddingModelName";

    /**
     * 摘要模型名称
     */
    String MODEL_NAME = "modelName";

    /**
     * 多模态模型名称
     */
    String MULTI_MODEL_NAME = "multiModelName";


    /* ====================faq抽取配置===============  */
    /**
     * FAQ抽取模型(faq抽取   faq润色  相似问生成)
     */
    String FAQ_MODEL_NAME = "faqModelName";

    /**
     * 单篇文档问答对抽取数量上限(0代表无限)
     */
    String FILE_FAQ_MAX_NUMS = "fileFaqMaxNums";

    /**
     * 一次性生成相似问个数(0代表无限)
     */
    String SIMILAR_QUESTION_MAX_NUMS = "similarQuestionMaxNums";

    /* ====================faq抽取配置===============  */

    /**
     * 图生成模型(大模型)
     */
    String GENERATE_GRAPH_MODEL_NAME = "generateGraphModelName";

    /**
     * 抽取实体类型
     */
    String GRAPH_PROMPT = "graphPrompt";


}
