package com.gientech.ragcommon.qa.request;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import java.math.BigDecimal;
import java.util.Date;

@Schema(name = "更新apikey的信息请求参数")
@Data
public class UpdateApiKeyInfoReq {

    @Schema(name = "id",description = "主键")
    private Long id;

    @Schema(name = "apiKey",description = "apikey全局唯一")
    private String apiKey;

    @Schema(name = "targetId",description = "目标id")
    private Integer targetId;

    @Schema(name = "status",description = "状态 0:禁用；1:正常 默认值1")
    private Integer status;

    @Schema(name = "bizType",description = "业务类型 1:助手配置")
    private Integer bizType;

    @Schema(name = "expireTime",description = "过期时间")
    private Date expireTime;

    @Schema(name = "isDel",description = "是否删除 -1 删除  1 正常 默认值1")
    private Integer isDel;

    @Schema(name = "modifyBy",description = "修改人")
    private String modifyBy;

}
