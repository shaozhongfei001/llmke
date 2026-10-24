package com.gientech.ragcommon.index.parameter;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONObject;
import com.alibaba.fastjson2.annotation.JSONField;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.gientech.ragcommon.index.dto.ModelSimpDTO;
import com.gientech.ragcommon.index.enmus.PlatFormEnums;
import com.google.common.collect.Lists;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.apache.commons.lang3.StringUtils;

import java.util.List;
import java.util.UUID;

import static com.gientech.ragcommon.index.constant.KbConfigConstant.*;

/**
 * 文件解析消息体
 */
@Data
@AllArgsConstructor
@NoArgsConstructor
public class FileParseTaskInfo {

    //    @JSONField(serialize = false)
    private Boolean isExtract = false;
    private Boolean isGraphParse = false;
    //    @JSONField(serialize = false)
    private String primitiveName;
    //    @JSONField(serialize = false)
    private Integer fileFaqMaxNums;
    //    @JSONField(serialize = false)
    private Integer similarQuestionMaxNums;
    @JSONField(serialize = false)
    private String messageId = UUID.randomUUID().toString();
    //    @JSONField(serialize = false)
    private Integer parseType;

    private boolean needAuth = true;

    /**
     * 当前用户
     */
//    @JSONField(serialize = false)
    private String userName;

    @JSONField(name = "user_id")
    @JsonProperty(value = "user_id")
    private String userId;
    private String apiKey;

    /**
     * ==================================以下是解析抽取文件的信息=====================================
     */

    /**
     * 知识库id
     */
    @JsonProperty("knowledge_base_id")
    private Long knowledgeBaseId;

    /**
     * 解析任务id
     */
    @JsonProperty("task_id")
    private Long taskId;

    /**
     * 知识库名称
     */
    @JsonProperty("knowledge_base_name")
    private String knowledgeBaseName;

    /**
     * 文件路径，和文件夹路径、文件ID列表不允许同时为空或者None
     */
    private List<FileParseTaskInfo.File> files;

    /**
     * 文本块大小(块token数) 默认500
     */
    @JsonProperty("chunk_size")
    private Integer chunkSize = 500;

    /**
     * 文本块重叠大小 默认20
     */
    @JsonProperty("chunk_overlap")
    private Integer chunkOverlap = 20;

    /**
     * 分段标识符
     */
    @JsonProperty("split_regex")
    private List<String> splitRegex;

    /**
     * 文档类型（解析方法），目前支持三种类型，[intelligent,naive, financial]
     */
    @JsonProperty("file_type")
    private String fileType = "intelligent";

    /*模型*/
    /**
     * 嵌入模型名称
     */
//    @JSONField(serialize = false)
//    @JsonProperty("embedding_model_name")
    private String embeddingModelName;

    /**
     * 多模态模型
     */
//    @JSONField(serialize = false)
    private String multiModelName;

    /**
     * 大模型
     */
//    @JSONField(serialize = false)
    private String modelName;

    /**
     * faq抽取  相似问  润色
     */
//    @JSONField(serialize = false)
    private String faqModelName;

    /**
     * 图抽取
     */
//    @JSONField(serialize = false)
    private String generateGraphModelName;

    /**
     * 是否将解析结果的文字全文保存到minio的txt文件中
     */
    @JsonProperty("save_txt")
    private boolean saveTxt = false;

    /**
     * 是否需要进行切分和索引
     */
    @JsonProperty("need_chunk")
    private boolean needChunk = true;

    /**
     * 抽取模型名称
     */
//    @JsonProperty("extract_model_name")
    private String extractModelName;

    @JsonProperty("index_name")
    private String indexName;

    @JsonProperty("model_info")
    private ModelSimpDTO modelInfo;

    @JsonProperty("embedding_model_info")
    private ModelSimpDTO embeddingNodelInfo;

    @JsonProperty("multi_model_info")
    private ModelSimpDTO multiModelInfo;

    public void adjustByPlatform(String platform, boolean chunking) {
        if (platform.equals(PlatFormEnums.INTELBRAIN_DW.getCode())) {
            this.needChunk = chunking;
            this.saveTxt = true;
        }
    }

    @Data
    public static class File {

        /**
         * 文件id
         */
        @JsonProperty("file_id")
        private Long fileId;

        /**
         * 文件路径
         */
        @JsonProperty("file_path")
        private String filePath;

        /**
         * 文件大小
         */
        @JsonProperty("file_size")
        private String fileSize;

        /**
         * 父文件名称
         */
        @JsonProperty("parent_file_name")
        private String parentFileName;

        /**
         * 解析类型
         */
        @JSONField(serialize = false)
        @JsonProperty("parse_type")
        private Integer parseType;

        @JsonProperty("folder_id")
        private Long folderId;

        private String[] labels;

        public void safeSetLabels(String label, String delimiter) {
            if (label == null || label.isEmpty() || !label.contains(delimiter)) {
                this.labels = new String[0];
                return;
            }
            this.labels = label.split(delimiter);
        }
    }

    public void buildKbConf(String config) {
        if (StringUtils.isEmpty(config))
            return;
        JSONObject confJson = JSON.parseObject(config);
        String splitRegex = confJson.getString(SPLIT_REGEX);
        this.chunkSize = confJson.getInteger(CHUNK_SIZE);
        this.setSplitRegex(StringUtils.isEmpty(splitRegex) ? Lists.newArrayList() : JSON.parseArray(splitRegex, String.class));
        this.setChunkOverlap(confJson.getInteger(CHUNK_OVERLAP));
        this.fileType = confJson.getString(FILE_TYPE);
        this.modelName = confJson.getString(MODEL_NAME);
        this.embeddingModelName = confJson.getString(EMBEDDING_MODEL_NAME);
        this.multiModelName = confJson.getString(MULTI_MODEL_NAME);
        this.faqModelName = confJson.getString(FAQ_MODEL_NAME);
        this.generateGraphModelName = confJson.getString(GENERATE_GRAPH_MODEL_NAME);
        this.fileFaqMaxNums = confJson.getInteger(FILE_FAQ_MAX_NUMS);
        this.similarQuestionMaxNums = confJson.getInteger(SIMILAR_QUESTION_MAX_NUMS);
    }


}
