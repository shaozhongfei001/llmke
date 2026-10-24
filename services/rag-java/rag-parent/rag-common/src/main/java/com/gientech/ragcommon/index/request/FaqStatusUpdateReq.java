package com.gientech.ragcommon.index.request;

import com.gientech.ragcommon.index.enmus.FaqStatusEnums;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(name = "更新faq状态请求参数")
@Data
public class FaqStatusUpdateReq {

    @NotNull(message = "kbId不能为空")
    @Schema(name = "kbId",description = "知识库id")
    private Long kbId;

    @Schema(name = "primitiveName",description = "源知识库名")
    private String primitiveName;

    @Schema(name = "fileIds",description = "文件ids")
    private List<Long> fileIds;

    @Schema(name = "folderIds",description = "文件夹id")
    private List<Long> folderIds;

    @Schema(name = "relatedpks",description = "relatedPks")
    List<Long> relatedpks;

    @Schema(name = "disabledRelatedpks",description = "禁用的FAQ的relatedPks")
    List<Long> disabledRelatedpks;

    @Schema(name = "status",description = "状态 0:禁用;1启用 默认值为1")
    private Integer status = FaqStatusEnums.ENABLED.getCode();
}
