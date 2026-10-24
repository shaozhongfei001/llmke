package com.gientech.ragcommon.index.request;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import java.math.BigDecimal;
import java.util.Date;

@Schema(name = "更新标签请求参数")
@Data
public class UpdateBizLabelReq {

    @Schema(name = "id",description = "id")
    private Long id;

    @Schema(name = "targetId",description = "资源id")
    private Long targetId;

    @Schema(name = "label",description = "label")
    private String label;

    @Schema(name = "bizType",description = "1:知识库;2:检索配置;3:模型;4:文件")
    private Integer bizType;

    @Schema(name = "isDel",description = "是否删除 -1 删除  1 正常 默认值1")
    private Integer isDel;

}
