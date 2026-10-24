package com.gientech.ragcommon.index.dto;

import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.annotation.JsonProperty;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.util.Date;

@Schema(name = "faq信息")
@Data
public class FaqParseDTO {

    @Schema(name = "id",description = "主键")
    private Long id;

    @Schema(name = "kbId",description = "知识库id")
    private Long kbId;

    @Schema(name = "fileName",description = "文件名称")
    private String fileName;

    @Schema(name = "fileSize",description = "文件大小 M")
    private Double fileSize;

    @Schema(name = "filePath",description = "文件路径")
    private String filePath;

    @Schema(name = "status",description = "faq解析状态  0:删除 1:正常 2:解析中，3:解析成功 4: 解析失败")
    private Integer status;

    @Schema(name = "uploadTime",description = "文件上传时间")
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss",timezone = "GMT+8")
    @JsonProperty("uploadTime")
    private Date gmtCreate;

    @Schema(name = "count",description = "问答对数")
    private Integer count;

}
