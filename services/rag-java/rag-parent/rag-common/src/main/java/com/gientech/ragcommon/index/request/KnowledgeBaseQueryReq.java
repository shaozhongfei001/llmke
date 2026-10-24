package com.gientech.ragcommon.index.request;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Schema(name = "知识库列表请求参数")
@Data
public class KnowledgeBaseQueryReq {

    @Schema(name = "fuzzy", description = "名称或id或标签")
    private String fuzzy;

    @Schema(name = "pageSize", description = "每页大小,默认值20")
    private Long pageSize = 20L;

    @Schema(name = "pageNo", description = "第几页 默认值1")
    private Long pageNo = 1L;

    private String platform;

    private String scope;

    private String userName;

    private boolean superAdmin;

    private Integer privateKB;

}
