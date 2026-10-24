package com.gientech.ragcommon.index.dto;


import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Schema(name = "文件集数据")
@Data
public class CollectDTO {

    @Schema(name = "parentFileName" , description = "文件集名称")
    private String parentFileName;

    @Schema(name = "groupId" , description = "文件集id（组id）")
    private String groupId;
}
