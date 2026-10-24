package com.gientech.ragcommon.index.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import lombok.Data;

import java.util.List;

@Schema(name = "faq创建请求参数")
@Data
public class FaqSaveOrUpdateReq {

    @Schema(name = "kbId",description = "知识库id")
    private Long kbId;

    @Schema(name = "fileId",description = "文件id")
    private Long fileId;

    @Schema(name = "folderId",description = "文件夹id")
    private Long folderId;

    @NotEmpty(message = "faqs不能为空")
    @Schema(name = "faqs",description = "需要修改或更新的问答对")
    private List<Faq> faqs;

    private boolean localSave;

    @Data
    public static class Faq{
        @Schema(name = "pk",description = "问答对id")
        private Long pk;

        @Schema(name = "relatedPk",description = "相似问答对关联id")
        private Long relatedPk;

        @Schema(name = "status",description = "启用状态，0:待启用，1：已启用")
        private Integer status;

        @Schema(name = "question",description = "问题")
        @NotBlank(message = "question不能为空")
        private String question;

        @Schema(name = "answer",description = "答案")
        @NotBlank(message = "answer不能为空")
        private String answer;

        @Schema(name = "labels",description = "标签")
        private List<String> labels;
    }
}
