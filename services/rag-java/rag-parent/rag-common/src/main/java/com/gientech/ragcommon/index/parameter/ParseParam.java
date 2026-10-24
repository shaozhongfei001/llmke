package com.gientech.ragcommon.index.parameter;

import com.alibaba.fastjson2.annotation.JSONField;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.gientech.ragcommon.index.dto.ModelSimpDTO;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.util.List;

/**
 * 文件解析消息体
 */
@Data
@AllArgsConstructor
@NoArgsConstructor
public class ParseParam {
    @JSONField(name = "user_id")
    @JsonProperty(value = "user_id")
    private String userId;

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
    private List<ParseParam.File> files;

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

    @JsonProperty("index_name")
    private String indexName;

    @JsonProperty("model_info")
    private ModelSimpDTO modelInfo;

    @JsonProperty("embedding_model_info")
    private ModelSimpDTO embeddingNodelInfo;

    @JsonProperty("multi_model_info")
    private ModelSimpDTO multiModelInfo;

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
    }

}
