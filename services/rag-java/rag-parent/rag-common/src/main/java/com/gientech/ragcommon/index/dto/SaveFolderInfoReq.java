package com.gientech.ragcommon.index.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Schema(name = "文件夹保存请求参数")
@Data
public class SaveFolderInfoReq {

    @Schema(name = "name", description = "文件夹名称")
    private String name;

    @Schema(name = "kbId", description = "知识库id")
    private Long kbId;

    @Schema(name = "parentId", description = "父文件夹id")
    private Long parentId;

    @Schema(name = "type", description = "1:文档解析；2:FAQ抽取")
    private Integer type;

}