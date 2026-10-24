package com.gientech.ragcommon.auth.request;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import java.math.BigDecimal;
import java.util.Date;

@Schema(name = "保存接口信息请求参数")
@Data
public class SaveInterfaceInfoReq {

    @Schema(name = "id",description = "资源id(appName+url+method的hash值)")
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

//    @Schema(name = "gmtCreate",description = "创建时间")
    private Date gmtCreate = new Date();

//    @Schema(name = "gmtModified",description = "更新时间")
    private Date gmtModified = new Date();

}
