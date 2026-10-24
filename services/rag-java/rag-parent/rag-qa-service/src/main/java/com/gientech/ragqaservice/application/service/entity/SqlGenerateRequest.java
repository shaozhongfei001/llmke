package com.gientech.ragqaservice.application.service.entity;

import com.alibaba.fastjson2.JSONArray;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.gientech.ragcommon.index.dto.ModelSimpDTO;
import com.gientech.ragqaservice.interfaces.resp.RetrieveDoc;
import lombok.Data;

import java.util.List;

import static com.gientech.ragcommon.qa.constant.AIConstant.MODEL_INFO;

/**
 * @author: shirleychen
 * @date 2025/8/29 10:09
 * @description
 */
@Data
public class SqlGenerateRequest {
    @JsonProperty("model_info")
    private ModelSimpDTO modelInfo;
    private String query;
    @JsonProperty("documents")
    private List<RetrieveDoc> retrieveDocList;

    public static SqlGenerateRequest from(String query, List<RetrieveDoc> retrieveDocList, ModelSimpDTO modelInfo) {
        SqlGenerateRequest sqlGenerateRequest = new SqlGenerateRequest();
        sqlGenerateRequest.setRetrieveDocList(retrieveDocList);
        sqlGenerateRequest.setModelInfo(modelInfo);
        sqlGenerateRequest.setQuery(query);
        return sqlGenerateRequest;
    }

//    public static SqlGenerateRequest from(String query, JSONArray retrieveDocList, ModelSimpDTO modelInfo) {
//        SqlGenerateRequest sqlGenerateRequest = new SqlGenerateRequest();
//        sqlGenerateRequest.setRetrieveDocList(retrieveDocList);
//        sqlGenerateRequest.setModelInfo(modelInfo);
//        sqlGenerateRequest.setQuery(query);
//        return sqlGenerateRequest;
//    }
}
