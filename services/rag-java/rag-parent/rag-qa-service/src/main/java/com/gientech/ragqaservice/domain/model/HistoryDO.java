package com.gientech.ragqaservice.domain.model;


import lombok.Data;
import java.io.Serializable;


@Data
public class HistoryDO implements Serializable {

    private static final long serialVersionUID = 1L;

    private Long answerId;

    private String queryContent;

    /**
     * 内容
     */
    private String answerContent;

    /**
     * 召回内容（json）
     */
    private String answerReference;
}
