package com.gientech.ragcommon.index.request;


import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.util.List;

@Schema(name = "文件集转移请求参数")
@Data
public class FileCollectTransferReq {

    @NotNull(message = "知识库id不能为空")
    @Schema(name = "kbId",description = "知识库id")
    private Long kbId;

    @Schema(name = "fileIds",description = "需要转移文件id")
    private List<Long> fileIds;

    @Schema(name = "srcGroupIds",description = "需要转移的文件集id")
    private List<String> srcGroupIds;

    @Schema(name = "parentFileName",description = "父文件(目标文件集名称)")
    private String parentFileName;

    @Schema(name = "groupId",description = "组id(目标组id)")
    private String groupId;

    @Schema(name = "fileListType",description = "列表类型: 1 文件解析列表；2 FAQ解析列表 默认值 1")
    private Integer fileListType = 1;
}
