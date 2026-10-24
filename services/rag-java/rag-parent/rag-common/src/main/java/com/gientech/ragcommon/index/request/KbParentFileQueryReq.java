package com.gientech.ragcommon.index.request;
import com.gientech.ragcommon.index.enmus.FileListTypeEnums;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Schema(name = "知识库父文件查询请求参数",requiredProperties = {"kbId"})
@Data
public class KbParentFileQueryReq {

    @NotNull(message = "kbId不能为空")
    @Schema(name = "kbId",description = "知识库id")
    private Long kbId;

    @Schema(name = "fileListType",description = "列表类型: 1 文件解析列表；2 FAQ解析列表 默认值 1")
    private Integer fileListType = FileListTypeEnums.FILE_LIST.getCode();

    @Schema(name = "pageNo",description = "第几页 默认值 1")
    private Long pageNo = 1L;

    @Schema(name = "pageSize",description = "每页大小 默认值 20")
    private Long pageSize = 20L;

}
