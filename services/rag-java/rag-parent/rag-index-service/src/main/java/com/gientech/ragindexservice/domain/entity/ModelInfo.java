package com.gientech.ragindexservice.domain.entity;

import com.gitee.sunchenbin.mybatis.actable.annotation.Column;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.Date;
import java.util.List;

/**
 * @Desc 模型管理
 * @Author ZhenPanHong
 * @Date 2025/3/5 13:35
 */
@Data
@Builder
@AllArgsConstructor
@NoArgsConstructor
public class ModelInfo implements Serializable {

    private static final long serialVersionUID = 1L;

    /**
     * 主键
     */
    private Long id;

    /**
     * 模型名称
     */
    private String modelName;

    /**
     * 模型使用类型: 1:LLM大语言模型、2:Embedding嵌入、3:rerank排序、4:MultiModel图片解析
     */
    private Integer type;

    /**
     * 模型传输协议,1-Baichuan、2-Qwen、3-GLM、4-openAI
     */
    private Integer modelProtocol;

    /**
     * 待接入的模型ID
     */
    private String modelIde;

    /**
     * APIkey
     */
    private String apiKey;

    /**
     * 请求URL
     */
    private String url;

    /**
     * 说明
     */
    private String dec;

    /**
     * 状态,0-不可用,1-可用,3-检测中
     *
     * @see com.gientech.ragcommon.index.enmus.ModelStatusEnums
     */
    private Integer status;

    /**
     * 报错信息
     */
    private String errorMsg;

    /**
     * 逻辑删除,0-未删除,1-已删除,默认为0
     */
    private String isDtl;

    /**
     * 溯源策略(deepseek相关模型的功能) 0:没有溯源策略 1:有溯源策略
     */
    private Integer trace;

    /**
     * 推理思考(qwen3相关模型的功能) 0:没有推理思考功能 1:有推理思考功能
     */
    private Integer thinking;

    /**
     * 创建时间
     */
    private Date gmtCreate;

    /**
     * 更新时间
     */
    private Date gmtModified;

    /**
     * 创建人
     */
    private String createBy;

    /**
     * 更新人
     */
    private String updateBy;

    /**
     * id集合
     */
    private List<Long> idList;
}