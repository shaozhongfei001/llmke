package com.gientech.ragcommon.index.dto;


import com.gientech.ragcommon.index.enmus.FaqListDataTypeEnums;
import com.google.common.collect.Lists;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.util.List;

@Schema(name = "文件夹详情")
@Data
public class FolderDTO {

    @Schema(name = "folderId", description = "文件夹")
    private Long folderId;

    @Schema(name = "fileId", description = "文件id")
    private Long fileId;

    @Schema(name = "name", description = "文件夹名称或文件名称")
    private String name;

    @Schema(name = "kbId", description = "知识库id")
    private Long kbId;

    @Schema(name = "dataType", description = "数据类型 1:文件夹 2 文件")
    private Integer dataType = FaqListDataTypeEnums.FOLDER.getCode();

    @Schema(name = "subs", description = "子文件或文件夹")
    private List<FolderDTO> subs = Lists.newArrayList();


}