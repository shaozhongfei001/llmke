package com.gientech.ragqaservice.interfaces.dto;

import com.alibaba.fastjson2.JSONArray;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.gientech.ragqaservice.interfaces.resp.RetrieveDoc;
import lombok.Data;

import java.util.List;

/**
 * @author chenjuan
 * @date 2025/6/24 14:21
 */
@Data
public class RetrieveData {
    @JsonProperty("faq_result_list")
    private List<Object> faqResultList;
    @JsonProperty("table_selected_list")
    private List<Object> tableSelectedList;
    @JsonProperty("documents_list")
    private List<RetrieveDoc> documentsList;
    @JsonProperty("database_documents")
    private List<RetrieveDoc> databaseDocuments;
}
