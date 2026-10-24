package com.gientech.ragcommon.index.request;

import com.gientech.ragcommon.auth.enums.BizTypeEnums;
import com.gientech.ragcommon.index.enmus.FolderTypeEnums;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.util.List;

/**
 * @author chenjuan
 * @date 2025/5/19 14:56
 */
@Schema(name = "查询文件夹参数")
@Data
public class QueryFolderReq {
    @NotNull(message = "kbId不能为空")
    @Schema(name = "kbId", description = "知识库id")
    private Long kbId;

    @NotNull(message = "type不能为空")
    @Schema(name = "type", description = "1:文档解析；2:FAQ抽取；3知识图谱；4:FAQ管理")
    private Integer type = FolderTypeEnums.FAQ_MANAGEMENT.getCode();

    @Schema(name = "currentId", description = "当前文件夹的id")
    private Long currentId;

    @Schema(name = "currentIds", description = "选择的文件夹ids，无需传文件的")
    private List<Long> currentIds;

    @Schema(name = "currentFileIds", description = "选择的faq文件id")
    private List<Long> currentFileIds;

}
