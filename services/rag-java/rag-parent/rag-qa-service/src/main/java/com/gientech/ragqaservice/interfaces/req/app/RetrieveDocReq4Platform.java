package com.gientech.ragqaservice.interfaces.req.app;

import com.gientech.ragcommon.qa.enmus.SearchPolicyEnums;
import lombok.Data;

import java.util.List;

/**
 * @author chenjuan
 * @date 2025/6/24 11:02
 */
@Data
public class RetrieveDocReq4Platform {
    /**
     * FAQ优先
     */
    private Boolean faqPriority;
    /**
     * 知识库id列表
     */
    private List<String> knowledge;
    /**
     * 是否开启知识图谱，当前默认关闭
     */
    private Boolean knowledgeGraphEnable;
    /**
     * 召回数
     */
    private Integer recallCount;
    /**
     * rerank功能
     */
    private Boolean rerankerEnabled;
    /**
     * 排序模型名称
     */
    private String rerankerModel;
    /**
     * 检索类型
     */
    private SearchPolicyEnums retrievalType;
    /**
     * 相似度阈值
     */
    private Double similarityThreshold;
    /**
     * 开启表格筛选
     */
    private Boolean tableFilterEnabled;
    /**
     * 用户知识库权限校验
     */
    private Boolean useAuth;
    /**
     * 用户输入
     */
    private String userQuestion;
}
