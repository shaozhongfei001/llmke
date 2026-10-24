package com.gientech.ragcommon.qa.dto;


import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import java.io.Serializable;


@Data
public class HistoryDTO implements Serializable {

    private static final long serialVersionUID = 1L;


    /**
     * 问题
     */
    @Schema(name = "queryContent",description ="问题")
    private String queryContent;

    /**
     * 回答
     */
    @Schema(name = "answerContent",description ="回答")
    private String answerContent;

    /**
     * 召回内容（json）
     */
    @Schema(name = "answerReference",description ="召回内容")
    private String answerReference;
}
