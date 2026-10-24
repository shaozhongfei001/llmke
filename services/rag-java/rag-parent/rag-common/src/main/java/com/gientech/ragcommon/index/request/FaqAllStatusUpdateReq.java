package com.gientech.ragcommon.index.request;

import com.gientech.ragcommon.index.enmus.FaqStatusEnums;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

@Builder
@NoArgsConstructor
@AllArgsConstructor
@Schema(name = "faq一键启用禁用请求参数",requiredProperties = {"kbId","pks"})
@Data
public class FaqAllStatusUpdateReq {

    @NotNull(message = "kbId不能为空")
    @Schema(name = "kbId",description = "知识库id")
    private Long kbId;

    @Schema(name = "fileId",description = "文件id")
    private Long fileId;

    @Schema(name = "disableRelatedPks",description = "禁用的FAQ的relatedPks")
    List<Long> disableRelatedPks;

    @Schema(name = "status",description = "状态 0:禁用;1启用 默认值为1")
    private Integer status = FaqStatusEnums.ENABLED.getCode();
}
