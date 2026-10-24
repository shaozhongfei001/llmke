package com.gientech.ragqaservice.application.service.entity;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.gientech.ragcommon.index.dto.ModelSimpDTO;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.compress.utils.Lists;

import java.io.Serializable;
import java.util.List;

/**
 * @author chenjuan
 * @date 2025/4/23 18:26
 */
@Data
@Slf4j
public class QuestionRecommendRequest implements Serializable {
    @JsonProperty("model_info")
    private ModelSimpDTO modelInfo;
    @JsonProperty("chat_history")
    private List<AiHistory> chatHistory;
    private String answer;
    private String query;
    @JsonProperty("top_k")
    private int topK = 3;

//    public void setAnswer(String answer) {
//        if(!StringUtils.isEmpty(answer)){
//            answer = answer.substring(answer.lastIndexOf("</think>") + 8);
//            String start = "[retrive-tag";
//            String end = "retrive-tag]";
//            // 转义开头和结尾中的特殊字符
//            String escapedStart = Pattern.quote(start);
//            String escapedEnd = Pattern.quote(end);
//            String regex = escapedStart + "(.*?)" + escapedEnd;
//            answer = answer.replaceAll(regex,"");
//            this.answer = answer;
//        }else
//            this.answer = "";
//
//    }
}
