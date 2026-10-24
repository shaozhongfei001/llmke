package com.gientech.ragcommon.index.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Schema(name = "重复FAQ的数据")
@Data
public class FaqRepeatDTO {

    @Schema(name = "pk",description = "FAQ的主键")
    private Long pk;

    @Schema(name = "question",description = "问题")
    private String question;

    @Schema(name = "answer",description = "答案")
    private String answer;

    @Schema(name = "status",description = "启用状态，0:待启用，1：已启用")
    private Integer status;

    @Schema(name = "sourceFile",description = "文件路径")
    private String sourceFile;

    @Schema(name = "sourceFileName",description = "文件名")
    private String sourceFileName;

}
