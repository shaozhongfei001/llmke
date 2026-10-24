package com.gientech.ragcommon.index.dto;
import com.fasterxml.jackson.annotation.JsonIgnore;
import com.fasterxml.jackson.databind.annotation.JsonSerialize;
import com.fasterxml.jackson.databind.ser.std.ToStringSerializer;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.util.Objects;


@Schema(name = "知识库详情")
@Data
public class KnowledgeBaseDTO {

    @JsonSerialize(using = ToStringSerializer.class)
    @Schema(name = "id", description = "主键")
    private Long id;

    @Schema(name = "kbName",description = "知识库名称")
    private String kbName;

    @Schema(name = "primitiveName",description = "知识库原始名称,对应算法知识库的名称")
    private String primitiveName;

    @Schema(name = "kbType",description = "知识库类型 1:知识库 2: 文档上传问答")
    private Integer kbType;

    @Schema(name = "kbDes",description = "描述")
    private String kbDes;

    @Schema(name = "sourceUrl",description = "路径")
    private String sourceUrl;

    @Schema(name = "status",description = "状态 0:删除;1正常，默认值1")
    private Integer status;

    @Schema(name = "fileTotalSize",description = "文件总大小 单位:M")
    private Double fileTotalSize;

    @Schema(name = "fileCount",description = "文件数量")
    private Integer fileCount;

    @Schema(name = "permission",description = "数据权限 0:无任何权限, 1: 读权限，2: 读写权限, 3: 所有权限")
    private Integer permission = 3;

    @Schema(name = "chunkSize",description = "文本块大小(块token数)")
    private Integer chunkSize;

    @Schema(name = "fileType",description = "文档类型（解析方法），目前支持三种类型，[intelligent,naive, financial]")
    private String fileType;

    @Schema(name = "chunkOverlap",description = "本块重叠大小")
    private Integer chunkOverlap;

    @Schema(name = "splitRegex",description = "分段标识符")
    private String splitRegex;

    @Schema(name = "embeddingModelName",description = "嵌入模型名称")
    private String embeddingModelName;

    @Schema(name = "modelName",description = "摘要模型")
    private String modelName;

    @Schema(name = "multiModelName",description = "多模态模型")
    private String multiModelName;

    @Schema(name = "faqModelName",description = "faq抽取,相似问 ,润色")
    private String faqModelName;

    @Schema(name = "generateGraphModelName",description = "图抽取模型")
    private String generateGraphModelName;

    @Schema(name = "kbLabel",description = "知识库标签")
    private String kbLabel;

    @Schema(name = "fileFaqMaxNums",description = "单篇文档问答对抽取数量上限")
    private Integer fileFaqMaxNums;

    @Schema(name = "similarQuestionMaxNums",description = "生成相似问个数")
    private Integer similarQuestionMaxNums;

    @Schema(name = "enablePolish",description = "faq导入是否润色 默认值false")
    private Boolean enablePolish = false;

    @Schema(name = "graphPrompt",description = "图谱提示词")
    private String graphPrompt;

    @Schema(name = "platform", description = "上层应用平台")
    private String platform;

    @Schema(name = "label", description = "标签")
    private String label;

    @JsonIgnore
    private String createBy;

    @Schema(name = "chunkType",description = "切片策略")
    private String chunkType;

    @Schema(name = "privateKb",description = "是否私有知识库")
    private Integer privateKb;

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        KnowledgeBaseDTO that = (KnowledgeBaseDTO) o;
        return id.equals(that.id);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id);
    }
}
