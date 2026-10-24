package com.gientech.ragqaservice.application.service.entity;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.gientech.ragcommon.index.dto.ModelSimpDTO;
import lombok.Data;

import java.util.List;

@Data
public class QuestionRewriteReq {

    private String query;

    @JsonProperty("model_info")
    private ModelSimpDTO modelInfo;

    @JsonProperty("chat_history")
    private List<AiHistory> chatHistory;
}
