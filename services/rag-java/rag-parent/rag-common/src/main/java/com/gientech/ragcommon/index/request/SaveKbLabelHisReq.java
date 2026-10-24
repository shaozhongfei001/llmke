package com.gientech.ragcommon.index.request;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import java.math.BigDecimal;
import java.util.Date;

@Schema(name = "保存请求参数")
@Data
public class SaveKbLabelHisReq {

    @Schema(name = "kbId",description = "知识库id")
    private Long kbId;

    @Schema(name = "labe",description = "知识库使用的标签")
    private String labe;

    @Schema(name = "isDel",description = "是否删除 -1 删除  1 正常 默认值1")
    private Integer isDel;

    @Schema(name = "modifyBy",description = "修改人")
    private String modifyBy;

}
