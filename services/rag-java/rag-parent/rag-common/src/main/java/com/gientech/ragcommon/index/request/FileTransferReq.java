package com.gientech.ragcommon.index.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Schema(name = "文件转移请求参数")
@Data
@AllArgsConstructor
@NoArgsConstructor
public class FileTransferReq {

    @NotNull(message = "targetFolderId不能为空")
    @Schema(name = "targetFolderId", description = "目标文件夹的id")
    private Long targetFolderId;

    @NotNull(message = "fileId不能为空")
    @Schema(name = "fileId", description = "文件id")
    private Long fileId;

}
