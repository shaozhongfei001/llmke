package com.gientech.ragcommon.index.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

/**
 * @Desc
 * @Author ZhenPanHong
 * @Date 2025/3/5 14:51
 */
@Schema(name = "模型信息详情")
@Data
public class ModelInfoDTO {

    @Schema(name = "id", description = "模型信息ID")
    private Long id;

    @Schema(name = "modelName", description = "模型名称")
    private String modelName;

    @Schema(name = "type", description = "模型使用类型: 1:LLM大语言模型、2:Embedding嵌入、3:rerank排序、4:MultiModel图片解析")
    private Integer type;

    @Schema(name = "modelProtocol", description = "模型传输协议,1-Baichuan、2-Qwen、3-GLM、4-openAI")
    private Integer modelProtocol;

    @Schema(name = "modelIde", description = "待接入的模型ID")
    private String modelIde;

    @Schema(name = "apiKey", description = "APIkey")
    private String apiKey;

    @Schema(name = "url", description = "请求URL")
    private String url;

    @Schema(name = "dec", description = "说明")
    private String dec;

    @Schema(name = "status", description = "状态,0-不可用,1-可用,3-检测中")
    private Integer status;

    @Schema(name = "errorMsg", description = "报错信息")
    private String errorMsg;

    @Schema(name = "permission", description = "0:无任何权限, 1: 读权限，2: 读写权限, 3: 所有权限")
    private Integer permission;

    @Schema(name = "trace", description = "溯源策略(deepseek相关模型的功能) 0:没有溯源策略 1:有溯源策略")
    private Boolean trace;

    @Schema(name = "thinking", description = "推理思考(qwen3相关模型的功能) 0:没有推理思考功能 1:有推理思考功能")
    private Boolean thinking;


}
