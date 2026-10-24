package com.gientech.ragcommon.qa.dto;

import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.alibaba.fastjson2.annotation.JSONField;
import lombok.Data;
import lombok.extern.slf4j.Slf4j;

@Data
@Slf4j
public class WebDocument {

    private JSONObject metadata;

    @JSONField(name = "page_content")
    private String pageContent;

    private String type;

    @JSONField(name = "order_num")
    private String orderNum;

    @JSONField(name = "pic_url_list")
    private JSONArray picUrlList;

    private JSONArray offset;
}
