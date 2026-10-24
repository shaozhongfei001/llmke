package com.gientech.ragcommon.index.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;
import java.util.Date;
import java.util.List;

@Schema(name = "保存标签请求参数")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SaveBizLabelReq {

    @Schema(name = "targetId",description = "资源id")
    @NotNull(message = "targetId不能为空")
    private Long targetId;

    @Schema(name = "label",description = "label")
    @NotNull(message = "label不能为空")
    private List<String> label;

    @Schema(name = "bizType",description = "1:知识库;2:检索配置;3:模型;4:文件")
    @NotNull(message = "bizType不能为空")
    private Integer bizType;

    @NotNull
    private String kbName;

}
