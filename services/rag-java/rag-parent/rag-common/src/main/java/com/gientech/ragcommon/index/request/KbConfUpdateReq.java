package com.gientech.ragcommon.index.request;

import com.alibaba.fastjson2.annotation.JSONField;
import com.fasterxml.jackson.annotation.JsonIgnore;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.gientech.ragcommon.index.enmus.KbConfigTypeEnums;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Schema(name = "知识库解析配置更新请求体",requiredProperties = {"id","chunkSize","fileType","embeddingModelName"})
@Data
public class KbConfUpdateReq {

    @JSONField(serialize = false)
    @Schema(name = "id",description = "知识库id")
    @NotNull(message = "知识库id不能为空")
    private Long id;

    @NotBlank(message = "fileType不能为空")
    @Schema(name = "fileType",description = "文档类型（解析方法），目前支持三种类型，[intelligent,naive, financial]")
    private String fileType = "intelligent";

    @NotNull(message = "chunkSize不能为空")
    @Schema(name = "chunkSize",description = "文本块大小(块token数)")
    private Integer chunkSize = 500;

    @Schema(name = "chunkOverlap",description = "本块重叠大小")
    private Integer chunkOverlap = 20;

    @Schema(name = "splitRegex",description = "分段标识符")
    private String splitRegex;

    @NotBlank(message = "embeddingModelName不能为空")
    @Schema(name = "embeddingModelName",description = "嵌入模型名称")
    private String embeddingModelName;

    @NotBlank(message = "modelName不能为空")
    @Schema(name = "modelName",description = "摘要模型")
    private String modelName;

    @NotBlank(message = "multiModelName不能为空")
    @Schema(name = "multiModelName",description = "多模态模型")
    private String multiModelName;

    @NotBlank(message = "faqModelName不能为空")
    @Schema(name = "faqModelName",description = "faq抽取,相似问 ,润色")
    private String faqModelName;

    @NotBlank(message = ("generateGraphModelName不能为空"))
    @Schema(name = "generateGraphModelName",description = "图抽取模型")
    private String generateGraphModelName;

    @Schema(name = "fileFaqMaxNums",description = "单篇文档问答对抽取数量上限")
    private Integer fileFaqMaxNums;

    @Schema(name = "similarQuestionMaxNums",description = "生成相似问个数")
    private Integer similarQuestionMaxNums;

    @Schema(name = "enablePolish",description = "faq导入是否润色 默认值false")
    private Boolean enablePolish = false;

    @Schema(name = "graphPrompt",description = "生成图谱的提示词")
    private String graphPrompt;

    @Schema(name = "kbConfigType",description = "配置编辑类型 1:知识解析配置;2:FAQ配置;3:知识图谱配置")
    private Integer kbConfigType = KbConfigTypeEnums.FILE_PARSE.getCode();
}
