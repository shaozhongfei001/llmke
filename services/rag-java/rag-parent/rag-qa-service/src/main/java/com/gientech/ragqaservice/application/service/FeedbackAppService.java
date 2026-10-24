package com.gientech.ragqaservice.application.service;

import com.alibaba.fastjson2.JSONObject;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.qa.dto.FeedbackDTO;
import com.gientech.ragcommon.qa.request.FeedbackQueryReq;
import com.gientech.ragcommon.qa.request.FeedbackReq;
import jakarta.servlet.http.HttpServletResponse;

import java.util.List;

public interface FeedbackAppService {
    
    Boolean feedback(FeedbackReq feedbackReq);

    Boolean cancel(String queryId);

    Page<FeedbackDTO> list(FeedbackQueryReq feedbackQueryReq);

    List<JSONObject> queList();

    void exportCsv(FeedbackQueryReq feedbackQueryReq, HttpServletResponse response);
}
