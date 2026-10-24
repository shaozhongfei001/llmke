package com.gientech.ragqaservice.interfaces.req.app;

import com.alibaba.nacos.shaded.com.google.gson.JsonObject;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.gientech.ragcommon.index.dto.ModelInfoDTO;
import lombok.Data;
import org.apache.commons.lang3.StringUtils;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

import static com.gientech.ragcommon.qa.constant.AIConstant.KNOWLEDGE_BASE_NAME;

/**
 * @author chenjuan
 * @date 2025/6/24 13:53
 */
@Data
public class RetrieveDocReq {
    @JsonProperty("enabled_graph")
    private Boolean enabledGraph;
    @JsonProperty("search_policy")
    private Integer searchPolicy;
    @JsonProperty("enabled_table_select")
    private Boolean enabledTableSelect;
    @JsonProperty("enabled_rerank")
    private Boolean enabledRerank;
    @JsonProperty("enabled_faq")
    private Boolean enabledFaq;
    @JsonProperty("top_k")
    private Integer topK;
    @JsonProperty("top_n")
    private Integer topN;
    private String query;
    private Boolean stream;
    @JsonProperty("knowledge_base_name")
    private List<String> knowledgeBaseName;
    @JsonProperty("score_threshold")
    private Double scoreThreshold;
    @JsonProperty("rerank_model_info")
    private RerankModel rerankModelInfo;
    @JsonProperty("database_name")
    private List<String> databaseName;
    @JsonProperty("condition_logic_operations")
    private String conditionLogicOperations;
    @JsonProperty("condition_json")
    private Condition conditionJson;

    @Data
    public static class RerankModel {
        private String url;
        @JsonProperty("model_name")
        private String modelName;
    }

    @Data
    public static class Condition {
        private List<String> labels;

        public Condition(List<String> labels) {
            this.labels = labels;
        }
    }

    public void convertKBN2Array(String knowledgeBaseName){
        if(StringUtils.isNotBlank(knowledgeBaseName)){
            this.knowledgeBaseName = Arrays.asList(knowledgeBaseName.split(";"));
        }else {
            this.knowledgeBaseName = List.of();
        }
    }
}
