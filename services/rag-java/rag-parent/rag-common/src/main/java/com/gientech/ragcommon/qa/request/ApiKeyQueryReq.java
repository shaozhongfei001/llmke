package com.gientech.ragcommon.qa.request;
import com.gientech.ragcommon.qa.enmus.ApiKeyBizTypeEnums;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Schema(name = "apiKey分页查询条件")
@Data
public class ApiKeyQueryReq {

    @Schema(name = "targetId",description = "业务目标数据id")
    private Long targetId;

    @Schema(name = "fuzzy",description = "appKey或id")
    private String fuzzy;

    @Schema(name = "status",description = "状态 0:禁用；1:正常 默认值1  null 所有")
    private Integer status;

    @Schema(name = "bizType",description = "业务类型 1:助手配置 默认值1")
    private Integer bizType = ApiKeyBizTypeEnums.QA_HELPER.getCode();

    @Schema(name = "pageNo",description = "第几页 默认值 1")
    private Long pageNo = 1L;

    @Schema(name = "pageSize",description = "每页大小 默认值 20")
    private Long pageSize = 20L;


}
