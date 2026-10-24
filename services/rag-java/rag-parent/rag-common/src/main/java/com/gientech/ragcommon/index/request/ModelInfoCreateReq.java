package com.gientech.ragcommon.index.request;

import com.gitee.sunchenbin.mybatis.actable.annotation.Column;
import com.gitee.sunchenbin.mybatis.actable.constants.MySqlTypeConstant;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

/**
 * @Desc
 * @Author ZhenPanHong
 * @Date 2025/3/5 14:37
 */
@Schema(name = "创建模型请求体", requiredProperties = {"modelName", "type", "modelIde", "url"})
@Data
public class ModelInfoCreateReq {

    @Schema(name = "modelName", description = "模型名称")
    @NotBlank(message = "模型名称不能为空")
    private String modelName;

    @Schema(name = "type", description = "模型使用类型: 1:LLM大语言模型、2:Embedding嵌入、3:rerank排序、4:MultiModel图片解析")
    @NotNull(message = "模型使用类型")
    private Integer type;

    @Schema(name = "model_protocol", description = "模型传输协议,1-Baichuan、2-Qwen、3-GLM、4-openAI")
    @NotNull(message = "模型传输协议")
    private Integer modelProtocol;

    @Schema(name = "modelIde", description = "待接入的模型ID")
    @NotBlank(message = "待接入的模型ID不能为空")
    private String modelIde;

    @Schema(name = "apiKey", description = "APIkey,除了类型为Xinference以外的情况都是必填")
    private String apiKey;

    @Schema(name = "url", description = "请求URL")
    @NotBlank(message = "URL不能为空")
    private String url;

    @Schema(name = "dec", description = "说明")
    private String dec;

//    @Schema(name = "trace", description = "溯源策略(deepseek相关模型的功能) 0:没有溯源策略 1:有溯源策略")
//    private Boolean trace = false;

    @Schema(name = "thinking", description = "推理思考(qwen3相关模型的功能) 0:没有推理思考功能 1:有推理思考功能")
    private Boolean thinking;
}
