package com.gientech.ragcommon.index.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Schema(name = "知识库更新请求体",requiredProperties = {"id","kbDes"})
@Data
public class KnowledgeBaseUpdateReq {

    @Schema(name = "id",description = "知识库id")
    @NotNull(message = "知识库id不能为空")
    private Long id;

    @Schema(name = "kbName",description = "知识库名称")
    @NotBlank(message = "知识库名称不能为空")
    private String kbName;

    @Schema(name = "kbDes",description = "描述")
    private String kbDes;

    @Schema(name = "kbLabel",description = "知识库标签")
    private String kbLabel;

    @Schema(name ="platform", description = "平台标识")
    private String platform;

}
