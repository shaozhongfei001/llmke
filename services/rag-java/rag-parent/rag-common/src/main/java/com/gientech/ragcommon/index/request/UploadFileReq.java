package com.gientech.ragcommon.index.request;

import com.gientech.ragcommon.index.enmus.FileListTypeEnums;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Schema(name = "文件上传请求参数",requiredProperties = {"kbId"})
@Data
public class UploadFileReq {

    @Schema(name = "kbId",description = "知识库id")
    @NotNull(message = "kbId不能为空")
    private Long kbId;

    @Schema(name = "fileListType",description = "列表类型: 1 文件解析列表；2 FAQ解析列表 默认值 1")
    private Integer fileListType = FileListTypeEnums.FILE_LIST.getCode();

    @Schema(name = "isParse",description = "是否解析 默认false")
    private Boolean isParse = false;

    @Schema(name = "isExtract",description = "是否抽取 默认 false")
    private Boolean isExtract = false;

    @Schema(name = "isOverwrite",description = "是否覆盖 默认true")
    private Boolean isOverwrite = true;

    private boolean chunking;
}
