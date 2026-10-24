package com.gientech.ragcommon.index.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.util.List;

@Schema(name = "修改文件启用禁用状态",requiredProperties = {"fileIds","enableStatus"})
@Data
public class FileEnableReq {

    @NotEmpty(message = "fileIds不能为空")
    @Schema(name = "fileIds",description = "文件id")
    private List<Long> fileIds;

    @NotNull(message = "enableStatus不能为空")
    @Schema(name = "enableStatus",description = "0:禁用; 1:启用")
    private Integer enableStatus;
}
