package com.gientech.ragcommon.auth.request;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import java.math.BigDecimal;
import java.util.Date;

@Schema(name = "更新接口信息请求参数")
@Data
public class UpdateInterfaceInfoReq {

    @Schema(name = "id",description = "主键")
    private Long id;

    @Schema(name = "appName",description = "应用名称")
    private String appName;

    @Schema(name = "appNameAbbreviate",description = "应用名称简称")
    private String appNameAbbreviate;

    @Schema(name = "name",description = "接口名称")
    private String name;

    @Schema(name = "url",description = "url")
    private String url;

    @Schema(name = "method",description = "接口的请求方式")
    private String method;

}
