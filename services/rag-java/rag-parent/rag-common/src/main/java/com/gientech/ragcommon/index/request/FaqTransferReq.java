package com.gientech.ragcommon.index.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.util.List;

@Schema(name = "faq转移请求参数")
@Data
public class FaqTransferReq {

    @NotNull(message = "kbId不能为空")
    @Schema(name = "kbId",description = "文件kbId")
    private Long kbId;

    @Schema(name = "fileIds",description = "文件ids")
    private List<Long> fileIds;

    @Schema(name = "folderIds",description = "文件夹ids")
    private List<Long> folderIds;

    @Schema(name = "relatedpks", description = "relatedpks")
    private List<Long> relatedpks;

    @Schema(name = "targetFileId",description = "目标文件(目标文件和文件夹不能同时有值)")
    private Long targetFileId;

    @Schema(name = "folderId", description = "目标文件(目标文件夹和文件夹不能同时有值)")
    private Long targetFolderId;
}
