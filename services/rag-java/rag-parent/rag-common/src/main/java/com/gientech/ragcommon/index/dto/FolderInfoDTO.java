package com.gientech.ragcommon.index.dto;

import com.fasterxml.jackson.annotation.JsonFormat;
import com.gitee.sunchenbin.mybatis.actable.annotation.Column;
import com.google.common.collect.Lists;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.util.Date;
import java.util.List;

@Schema(name = "文件夹详情")
@Data
public class FolderInfoDTO {

    @Schema(name = "id", description = "主键")
    private Long id;

    @Schema(name = "name", description = "文件夹名称")
    private String name;

    @Schema(name = "kbId", description = "知识库id")
    private Long kbId;

    @Schema(name = "type", description = "1:文档解析；2:FAQ抽取")
    private Integer type;

    @Schema(name = "parentId", description = "父文件夹id")
    private Long parentId;

    @Schema(name = "folderLabel", description = "文件夹标签")
    private String folderLabel;

    @Schema(name = "status", description = "1：正常；-1：删除")
    private Integer status;

    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss", timezone = "GMT+8")
    @Schema(name = "gmtCreate", description = "创建时间")
    private Date gmtCreate;

    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss", timezone = "GMT+8")
    @Schema(name = "gmtModified", description = "更新时间")
    private Date gmtModified;

    @Schema(name = "createBy", description = "创建人")
    private String createBy;

    @Schema(name = "updateBy", description = "更新人")
    private String updateBy;

    @Schema(name = "fullPath", description = "完整路径（包含结尾/)")
    private String fullPath;

    @Schema(name = "subFolder", description = "子目录")
    private List<FolderInfoDTO> subFolders = Lists.newArrayList();

}