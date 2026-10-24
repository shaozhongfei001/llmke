package com.gientech.ragcommon.qa.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import com.fasterxml.jackson.annotation.JsonFormat;
import java.util.Date;
import java.math.BigDecimal;

@Schema(name = "apikey的信息")
@Data
public class ApiKeyInfoDTO {

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

    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss",timezone = "GMT+8")
    @Schema(name = "expireTime",description = "过期时间")
    private Date expireTime;

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
