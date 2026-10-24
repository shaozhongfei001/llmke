package com.gientech.ragcommon.qa.request;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Schema(name = "配置文件查询条件")
@Data
public class SearchConfigQueryReq {

    @Schema(name = "nameOrId",description = "配置名称或者id")
    private String fuzzy;

    @Schema(name = "pageNo",description = "第几页 默认值 1")
    private Long pageNo = 1L;

    @Schema(name = "pageSize",description = "每页大小 默认值 20")
    private Long pageSize = 20L;


}
