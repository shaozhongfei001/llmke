package com.gientech.ragcommon.index.request;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Builder;
import lombok.Data;

@Builder
@Data
public class FolderAndFilerReq {

    @Schema(name = "userId", description = "用户Id")
    private Long userId;

    @Schema(name = "kbId", description = "知识库id")
    private Long kbId;

    @Schema(name = "folderId", description = "文件夹id")
    private Long folderId;

    @Schema(name = "fileId",description = "文件id")
    private Long fileId;

    @Schema(name = "fuzzy", description = "关键字查询")
    private String fuzzy;

}
