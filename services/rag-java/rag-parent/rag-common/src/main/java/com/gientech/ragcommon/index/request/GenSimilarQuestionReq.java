package com.gientech.ragcommon.index.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.util.List;


@Schema(name = "faq相似问生成")
@Data
public class GenSimilarQuestionReq {

    @NotNull(message = "kbId不能为空")
    @Schema(name = "kbId",description = "知识库id")
    private Long kbId;

    @Schema(name = "fileIds",description = "文件ids")
    private List<Long> fileIds;

    @Schema(name = "folderIds",description = "文件夹id")
    private List<Long> folderIds;

    @Schema(name = "relatedPks",description = "问答对relatedPk")
    private List<Long> relatedPks;

}
