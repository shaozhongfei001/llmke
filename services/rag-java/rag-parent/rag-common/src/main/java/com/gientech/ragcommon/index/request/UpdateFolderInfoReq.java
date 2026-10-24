package com.gientech.ragcommon.index.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Schema(name = "文件夹更新请求参数")
@Data
public class UpdateFolderInfoReq {

    @NotNull(message = "id不能为空")
    @Schema(name = "id", description = "主键")
    private Long id;

    @NotNull(message = "kbId不能为空")
    @Schema(name = "kbId", description = "知识库id")
    private Long kbId;

    @Schema(name = "parentId", description = "父文件夹id")
    private Long parentId;

    @NotBlank(message = "name不能为空")
    @Schema(name = "name", description = "文件夹名称")
    private String name;

    @Schema(name = "type", description = "1:文档解析；2:FAQ抽取; 3;知识图谱 4:FAQ管理创建的文件夹或者从FAQ抽取复制的文件夹")
    private Integer type;

}