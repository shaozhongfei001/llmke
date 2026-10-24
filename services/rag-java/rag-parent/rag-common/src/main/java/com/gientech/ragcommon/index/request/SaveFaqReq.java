package com.gientech.ragcommon.index.request;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import java.math.BigDecimal;
import java.util.Date;

@Schema(name = "保存请求参数")
@Data
public class SaveFaqReq {

    @Schema(name = "pk",description = "milvus的id")
    private Long pk;

    @Schema(name = "relatedPk",description = "相似问的id")
    private Long relatedPk;

    @Schema(name = "fileId",description = "文件id")
    private Long fileId;

    @Schema(name = "folderId",description = "文件夹id")
    private Long folderId;

    @Schema(name = "isDel",description = "1-正常 0-删除")
    private Integer isDel;

}
