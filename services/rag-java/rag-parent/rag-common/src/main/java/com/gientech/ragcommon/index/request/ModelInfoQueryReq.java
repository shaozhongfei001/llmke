package com.gientech.ragcommon.index.request;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

/**
 * @Desc
 * @Author ZhenPanHong
 * @Date 2025/3/5 15:30
 */
@Schema(name = "查询模型请求参数")
@Data
public class ModelInfoQueryReq {

    @Schema(name = "modelName", description = "模型名称")
    private String modelName;

    @Schema(name = "type", description = "模型使用类型: 1:LLM大语言模型、2:Embedding嵌入、3:rerank排序、4:MultiModel图片解析")
    private Integer type;

    @Schema(name = "status", description = "模型状态,0-不可用,1-可用")
    private Integer status;

    @Schema(name = "pageSize", description = "每页大小,默认值20")
    private Long pageSize = 20L;

    @Schema(name = "pageNo", description = "第几页 默认值1")
    private Long pageNo = 1L;

    private boolean needAuth = true;


}
