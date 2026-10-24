package com.gientech.ragcommon.index.request;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Schema(name = "创建知识库请求体",requiredProperties = {"kbName","primitiveName"})
@Data
public class KnowledgeBaseCreateReq {

    @Schema(name = "kbName", description = "知识库名称")
    @NotBlank(message="知识库名称不能为空！")
    private String kbName;

//    @Schema(name = "primitiveName", description = "知识库原始名称,对应算法知识库的名称")
//    @NotBlank(message="知识库原始名称不能为空！")
//    private String primitiveName;

    @Schema(name = "kbType",description = "知识库类型 1:知识库 2: 文档上传问答 默认值是1")
    private Integer kbType = 1;

    @Schema(name = "kbDes",description = "描述")
    private String kbDes;

    @NotBlank(message = "fileType不能为空")
    @Schema(name = "fileType",description = "文档类型（解析方法），目前支持三种类型，[intelligent,naive, financial]")
    private String fileType = "intelligent";

    @NotNull(message = "chunkSize不能为空")
    @Schema(name = "chunkSize",description = "文本块大小(块token数)")
    private Integer chunkSize = 500;

    @Schema(name = "chunkOverlap",description = "文本块重叠大小")
    private Integer chunkOverlap = 0;

    @Schema(name = "splitRegex",description = "分段标识符")
    private String splitRegex;

    @Schema(name = "embeddingModelName",description = "嵌入模型名称")
    private String embeddingModelName;

    @Schema(name = "kbLabel",description = "知识库标签")
    private String kbLabel;

    @Schema(name = "graphPrompt",description = "生成图谱的提示词")
    private String graphPrompt;

    @Schema(name = "multiModelName",description = "多模态模型名称")
    private String multiModelName;

    @Schema(name = "privateKb",description = "是否私有知识库 0:非私有 1: 私有 默认值是0")
    private Integer privateKb = 0;

    private String platform;

    private String userId;

    private String userName;


    public void putHeaders(String platform, String userId) {
        this.platform = platform;
        this.userId = userId;
    }
}
