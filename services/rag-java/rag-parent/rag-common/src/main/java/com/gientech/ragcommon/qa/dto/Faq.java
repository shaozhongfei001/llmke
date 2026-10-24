package com.gientech.ragcommon.qa.dto;

import com.alibaba.fastjson2.annotation.JSONField;
import lombok.Data;

@Data
public class Faq {

    @JSONField(name = "faq_question")
    private String question;

    @JSONField(name = "faq_answer")
    private String answer;

    @JSONField(name = "score")
    private String score;

}
