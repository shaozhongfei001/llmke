package com.gientech.ragqaservice.domain.entity;

import com.alibaba.fastjson2.JSONObject;

public class FaqSelectInfo {

    private JSONObject faqDataJson;

    public FaqSelectInfo(JSONObject faqDataJson) {
        this.faqDataJson = faqDataJson;
    }

    public JSONObject getData(){
        return faqDataJson.getJSONObject("data");
    }

    public JSONObject getMetadata(){
        JSONObject data = getData();
        return data.getJSONObject("metadata");
    }

    public String getAnswer(){
        JSONObject metadata = getMetadata();
        return metadata.getString("answer");
    }

    public String getQuestion(){
        JSONObject metadata = getMetadata();
        return metadata.getString("question");
    }
}
