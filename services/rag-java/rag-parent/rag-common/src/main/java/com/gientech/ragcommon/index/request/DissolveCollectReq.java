package com.gientech.ragcommon.index.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import lombok.Data;


import java.util.List;

@Schema(name = "文件集解散请求参数")
@Data
public class DissolveCollectReq {

    @NotNull(message  = "kbId不能为空")
    @Schema(name = "kbId",description = "知识库id")
    private Long kbId;

    @NotEmpty(message = "groupIds不能为空")
    @Schema(name = "groupIds",description = "文件集id")
    private List<String> groupIds;

    @Schema(name = "fileListType",description = "列表类型: 1 文件解析列表；2 FAQ解析列表 默认值 1")
    private Integer fileListType = 1;
}
