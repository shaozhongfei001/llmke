package com.gientech.ragcommon.index.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;


@Schema(name = "faq相似问新增",requiredProperties = {"kbId","pk","similarQuestion"})
@Data
public class SimilarQuestionReq {

    @NotNull(message = "kbId不能为空")
    @Schema(name = "kbId",description = "知识库id")
    private Long kbId;

    @Schema(name = "fileId",description = "文件id")
    private Long fileId;

    @Schema(name = "relatedPk",description = "相似问关联id")
    private Long relatedPk;

    @NotNull(message = "pk不能为空")
    @Schema(name = "pk",description = "问答对id")
    private Long pk;

    @NotBlank(message = "similarQuestion不能为空")
    @Schema(name = "similarQuestion",description = "相识问题")
    private String similarQuestion;
}
