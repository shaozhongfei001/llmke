package com.gientech.ragcommon.qa.dto;

import com.alibaba.fastjson2.annotation.JSONField;
import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.util.Date;
import java.util.List;

@Data
public class FeedbackDTO {

    /**
     * 答案id
     */
    private Long answerId;

    /**
     * 0：踩；1：赞
     */
    private Integer restult;

    /**
     * 用户登录名
     */
    private String userName;

    /**
     * 用户真实名称
     */
    private String userRealname;

    /**
     * 部门名称
     */
    private String deptName;

    /**
     * 手机
     */
    private String userPhone;

    /**
     * 理解问题有误
     */
    private String queError;

    /**
     * 回答不佳
     */
    private String ansPoor;

    /**
     * 格式错误
     */
    private String formatError;

    /**
     * 有害信息
     */
    private String harmfulInfo;

    /**
     * 其他
     */
    private String othres;

    /**
     * 补充说明
     */
    private String supplementExplain;

    /**
     * 理想回答
     */
    private String idealAnswer;

    @JsonProperty("feedbackTime")
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss",timezone = "GMT+8")
    private Date gmtCreate;

    /**
     * 用户问题
     */
    private String qestion;

    /**
     * 模型回答
     */
    private String anwser;

    /**
     * 助手名称
     */
    private String configName;

    /**
     * 历史内容
     */
    private List<HistoryDTO> historyDTOList;
}
