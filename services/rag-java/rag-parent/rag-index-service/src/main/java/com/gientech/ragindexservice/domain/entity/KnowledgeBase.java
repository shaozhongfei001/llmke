package com.gientech.ragindexservice.domain.entity;

import com.alibaba.fastjson2.JSONObject;
import com.gientech.ragcommon.index.enmus.PlatFormEnums;
import com.gientech.ragcommon.index.request.KnowledgeBaseCreateReq;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import org.apache.commons.lang3.StringUtils;

import java.io.Serializable;
import java.util.Date;
import java.util.Objects;

import static com.gientech.ragcommon.index.constant.KbConfigConstant.*;

/**
 * <p>
 * 知识库
 * </p>
 *
 * @author wudf
 * @since 2024-06-04
 */
@Data
public class KnowledgeBase implements Serializable {

    private static final long serialVersionUID = 1L;

    private Long id;

    /**
     * 知识库名称
     */
    private String kbName;

    /**
     * 知识库原始名称,对应算法知识库的名称
     */
    private String primitiveName;

    /**
     * 知识库类型 1:知识库 2: 文档上传问答
     */
    private Integer kbType;

    /**
     * 描述
     */
    private String kbDes;

    /**
     * 路径
     */
    private String sourceUrl;

    /**
     * 状态 0:删除;1正常，默认值1
     */
    private Integer status;

    /**
     * 知识库解析配置
     */
    private String config;

    /**
     * 知识标签
     */
    private String kbLabel;

    /**
     * 创建人
     */
    private String createBy;

    /**
     * 创建时间
     */
    private Date gmtCreate;

    /**
     * 修改人
     */
    private String modifyBy;

    /**
     * 修改时间
     */
    private Date gmtModified;

    /**
     * 数据权限 0:无任何权限, 1: 读权限，2: 读写权限, 3: 所有权限
     */
    private Integer permission;


    /**
     * ================知识库配置====================
     */

    /**
     * 文本块大小(块token数) 默认500
     */
    private Integer chunkSize = 500;

    /**
     * 嵌入模型名称
     */
    private String embeddingModelName;

    /**
     * 大模型
     */
    private String modelName;

    /**
     * 多模态模型
     */
    private String multiModelName;

    /**
     * faq抽取,相似问 ,润色
     */
    private String faqModelName;

    /**
     * 图抽取模型
     */
    private String generateGraphModelName;

    /**
     * 单篇文档问答对抽取数量上限
     */
    private Integer fileFaqMaxNums;

    /**
     * 生成相似问个数
     */
    private Integer similarQuestionMaxNums;

    /**
     * faq导入是否润色 默认值false
     */
    private Boolean enablePolish = false;

    /**
     * 图谱提示词
     */
    private String graphPrompt;

    /**
     * 文档类型（解析方法），目前支持三种类型，[intelligent,naive, financial]
     */
    private String fileType;

    /**
     * 本块重叠大小
     */
    private Integer chunkOverlap;

    /**
     * 分段标识符
     */
    private String splitRegex;


    private String platform = "rag-qa";

    /**
     * 是否私有知识库：0：非私有 1：私有
     */
    private Integer privateKb;


    public Integer getChunkSize() {
        if (StringUtils.isNotEmpty(config))
            return JSONObject.parse(config).getInteger(CHUNK_SIZE);
        return chunkSize;
    }

    public Integer getChunkOverlap() {
        if (StringUtils.isNotEmpty(config))
            return JSONObject.parse(config).getInteger(CHUNK_OVERLAP);
        return chunkOverlap;
    }

    public String getsplitRegex() {
        if (StringUtils.isNotEmpty(config))
            return JSONObject.parse(config).getString(SPLIT_REGEX);
        return splitRegex;
    }

    public String getFileType() {
        if (StringUtils.isNotEmpty(config))
            return JSONObject.parse(config).getString(FILE_TYPE);
        return fileType;
    }

    public String getEmbeddingModelName() {
        if (StringUtils.isNotEmpty(config))
            return JSONObject.parse(config).getString(EMBEDDING_MODEL_NAME);
        return embeddingModelName;
    }

    public String getModelName() {
        if (StringUtils.isNotEmpty(config))
            return JSONObject.parse(config).getString(MODEL_NAME);
        return embeddingModelName;
    }

    public String getMultiModelName() {
        if (StringUtils.isNotEmpty(config))
            return JSONObject.parse(config).getString(MULTI_MODEL_NAME);
        return embeddingModelName;
    }

    public String getFaqModelName() {
        if (StringUtils.isNotEmpty(config))
            return JSONObject.parse(config).getString(FAQ_MODEL_NAME);
        return embeddingModelName;
    }

    public String getGenerateGraphModelName() {
        if (StringUtils.isNotEmpty(config))
            return JSONObject.parse(config).getString(GENERATE_GRAPH_MODEL_NAME);
        return embeddingModelName;
    }

    public Integer getFileFaqMaxNums() {
        if (StringUtils.isNotEmpty(config))
            return JSONObject.parse(config).getInteger("fileFaqMaxNums");
        return fileFaqMaxNums;
    }

    public Integer getSimilarQuestionMaxNums() {
        if (StringUtils.isNotEmpty(config))
            return JSONObject.parse(config).getInteger("similarQuestionMaxNums");
        return similarQuestionMaxNums;
    }

    public Boolean getEnablePolish() {
        if (StringUtils.isNotEmpty(config)) {
            Boolean enablePolish = JSONObject.parse(config).getBoolean("enablePolish");
            return !Objects.isNull(enablePolish) && enablePolish;
        }
        return enablePolish;
    }

    public String getGraphPrompt() {
        if (StringUtils.isNotEmpty(config)) {
            return JSONObject.parse(config).getString("graphPrompt");
        }
        return graphPrompt;
    }

    public String getPrimitiveName() {
        if (Objects.isNull(this.id)) {
            return this.primitiveName;
        }

        return this.platform.equals(PlatFormEnums.RAG_QA.getCode()) ? this.primitiveName : String.valueOf(this.id);
    }

    public String getRealPrimitiveName() {
        return this.primitiveName;
    }
}
