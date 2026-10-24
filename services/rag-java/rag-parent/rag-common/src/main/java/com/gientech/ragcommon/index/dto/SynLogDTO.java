package com.gientech.ragcommon.index.dto;

import lombok.Data;

import java.io.Serializable;

@Data
public class SynLogDTO implements Serializable {

    private Long id;

    /**
     * 知识库id
     */
    private Long kbId;

    /**
     * 目标id（知识库id）
     */
    private Long targetId;

    /**
     * 日志类型 1:文件解析;2FAQ抽取
     */
    private Integer logType;

    /**
     * 异常码 (如果为-1的话，接口不可用)
     */
    private String errorCode;

    /**
     * 异常信息
     */
    private String errorMessage;

    /**
     * 异常信息详情
     */
    private String errorDetail;

}
