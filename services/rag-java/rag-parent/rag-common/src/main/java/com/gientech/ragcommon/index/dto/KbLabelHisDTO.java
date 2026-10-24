package com.gientech.ragcommon.index.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import com.fasterxml.jackson.annotation.JsonFormat;
import java.util.Date;
import java.math.BigDecimal;

@Schema(name = "")
@Data
public class KbLabelHisDTO {

    private Long id;

    @Schema(name = "kbId",description = "知识库id")
    private Long kbId;

    @Schema(name = "labe",description = "知识库使用的标签")
    private String labe;

    @Schema(name = "isDel",description = "是否删除 -1 删除  1 正常 默认值1")
    private Integer isDel;

    @Schema(name = "createBy",description = "创建人")
    private String createBy;

    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss",timezone = "GMT+8")
    @Schema(name = "gmtCreate",description = "创建时间")
    private Date gmtCreate;

    @Schema(name = "modifyBy",description = "修改人")
    private String modifyBy;

    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss",timezone = "GMT+8")
    @Schema(name = "gmtModified",description = "修改时间")
    private Date gmtModified;

}
