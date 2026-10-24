package com.gientech.ragcommon.graph.entity;

import com.alibaba.fastjson.JSONObject;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@NoArgsConstructor
@AllArgsConstructor
@Data
public class Keyword {

    private String vid;

    private String nodeType;

    private JSONObject properties;

}
