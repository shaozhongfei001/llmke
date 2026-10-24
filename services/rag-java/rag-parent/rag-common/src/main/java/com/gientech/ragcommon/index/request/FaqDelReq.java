package com.gientech.ragcommon.index.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.util.List;

@Schema(name = "faq删除请求参数")
@Data
public class FaqDelReq {

    @NotNull(message = "kbId不能为空")
    @Schema(name = "kbId",description = "文件kbId")
    private Long kbId;

    @Schema(name = "fileIds",description = "文件ids")
    private List<Long> fileIds;

    @Schema(name = "folderIds",description = "文件夹ids")
    private List<Long> folderIds;

//    @Schema(name = "pks",description = "文件pks")
//    private List<Long> pks;
}
