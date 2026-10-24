package com.gientech.ragcommon.graph.dto;

import com.alibaba.fastjson.JSONObject;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@NoArgsConstructor
@AllArgsConstructor
@Data
public class KeywordDTO {

    private String vid;

    private String nodeType;

    private JSONObject properties;
}
