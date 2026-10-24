package com.gientech.ragindexservice.domain.entity;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.databind.annotation.JsonDeserialize;
import com.gientech.ragcommon.auth.enums.BizTypeEnums;
import com.gientech.ragindexservice.infrastructure.deserializer.DateDeserializer;
import lombok.Data;
import org.springframework.util.CollectionUtils;

import java.util.Date;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.stream.Collectors;

/**
 * @author chenjuan
 * @date 2025/5/14 10:50
 */
@Data
public class FaqEsInfo {
    @JsonProperty("total_count")
    private long totalCount;
    @JsonProperty("result_data")
    private List<FaqEsInfoResultData> resultData;


    @Data
    public static class FaqEsInfoResultData {
        @JsonProperty("_index")
        private String index;
        @JsonProperty("_id")
        private String id;
        @JsonProperty("_source")
        private FaqEsInfoSource source;
    }

    @Data
    public static class FaqEsInfoSource {
        @JsonProperty("page_content")
        private String pageContent;
        private FaqEsMetadata metadata;
    }

    @Data
    public static class FaqEsMetadata {
        private String source;
        @JsonProperty("document_id")
        private String documentId;
        @JsonProperty("folder_id")
        private String folderId;
        private Set<String> labels;
        @JsonProperty("knowledge_base_name")
        private String knowledgeBaseName;
        private String pk;
        @JsonProperty("related_pk")
        private String relatedPk;
        private String question;
        private String answer;
        @JsonProperty("order_num")
        private Long orderNum;
        private Integer status;
        @JsonProperty("faq_type")
        private Integer faqType;
        @JsonProperty("create_time")
        @JsonDeserialize(using = DateDeserializer.class)
        private Date createTime;
        @JsonProperty("update_time")
        @JsonDeserialize(using = DateDeserializer.class)
        private Date updateTime;


        public Set<String> getLabels() {
            if (CollectionUtils.isEmpty(this.labels)) {
                this.labels = new HashSet<>();
            }
            return labels;
        }

        public Set<BizLabel> getBizLabels(){
            if(CollectionUtils.isEmpty(this.labels)){
                return Set.of();
            }
            return this.labels.stream().map(label->BizLabel.builder().label(label).bizType(BizTypeEnums.FAQ.getCode()).targetId(Long.valueOf(pk)).build()).collect(Collectors.toSet());
        }
    }
}
