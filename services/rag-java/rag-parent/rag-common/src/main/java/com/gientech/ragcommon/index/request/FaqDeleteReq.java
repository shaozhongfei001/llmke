package com.gientech.ragcommon.index.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;

import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import lombok.Builder;
import lombok.Data;

import java.util.List;

@Schema(name = "faq删除参数")
@Data
public class FaqDeleteReq {

    @NotNull(message = "kbId不能为空")
    @Schema(name = "kbId",description = "文件kbId")
    private Long kbId;

    @Schema(name = "fileIds",description = "文件ids")
    private List<Long> fileIds;

    @Schema(name = "folderIds",description = "文件夹id")
    private List<Long> folderIds;

    @Schema(name = "relatedPks",description = "relatedPks")
    private List<Long> relatedPks;

    @Schema(name = "pks",description = "pks")
    private List<Long> pks;
}
