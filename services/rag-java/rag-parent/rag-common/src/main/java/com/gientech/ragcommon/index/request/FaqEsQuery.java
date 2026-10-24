package com.gientech.ragcommon.index.request;

import com.alibaba.fastjson.annotation.JSONField;
import com.alibaba.fastjson2.JSONObject;
import lombok.Data;

import java.util.List;

/**
 * @author chenjuan
 * @date 2025/5/14 14:25
 */
@Data
public class FaqEsQuery {
    @JSONField(name = "index_name")
    private List<String> indexName;
    @JSONField(name = "sort_field")
    private String sortField = "update_time";
    @JSONField(name = "sort_mode")
    private String sortMode = "desc";
    @JSONField(name = "page_no")
    private Integer pageNo;
    @JSONField(name = "page_num")
    private Integer pageSize;
    @JSONField(name = "document_id")
    private String documentId;
    @JSONField(name = "condition_json")
    private List<JSONObject> conditionJson;
    @JSONField(name = "condition_logic_operations")
    private String conditionLogicOperations;

    @Data
    public static class EsConditionQuery {

        private List<Integer> status;
        private List<Long> pk;
        @JSONField(name = "related_pk")
        private List<Long> relatedPk;
        @JSONField(name = "faq_type")
        private Integer faqType;
        @JSONField(name = "page_content")
        private List<String> pageContent;
        private List<String> answer;
    }

    public String toJSONString(){
        return JSONObject.toJSONString(this);
    }
}
