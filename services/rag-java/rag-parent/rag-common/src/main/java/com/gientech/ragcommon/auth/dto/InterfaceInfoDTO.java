package com.gientech.ragcommon.auth.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import com.fasterxml.jackson.annotation.JsonFormat;
import java.util.Date;
import java.math.BigDecimal;

@Schema(name = "接口信息")
@Data
public class InterfaceInfoDTO {

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

    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss",timezone = "GMT+8")
    @Schema(name = "gmtCreate",description = "创建时间")
    private Date gmtCreate;

    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss",timezone = "GMT+8")
    @Schema(name = "gmtModified",description = "更新时间")
    private Date gmtModified;

    @Schema(name = "createBy",description = "创建人")
    private String createBy;

    @Schema(name = "updateBy",description = "更新人")
    private String updateBy;

    private Long resourceId;

    private String resourceName;

    private Integer resourceType;

}
