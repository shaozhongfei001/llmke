package com.gientech.ragcommon.index.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.util.List;

@Schema(name = "文件集编辑请求参数")
@Data
public class RemoveCollectReq {

    @NotNull(message  = "kbId不能为空")
    @Schema(name = "kbId",description = "知识库id")
    private Long kbId;

    @NotEmpty(message = "fileIds不能为空")
    @Schema(name = "fileIds",description = "文件id")
    private List<Long> fileIds;

//    @Schema(name = "groupIds",description = "文件集id")
//    private List<String> groupIds;
}
