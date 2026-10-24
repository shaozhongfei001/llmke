package com.gientech.ragcommon.auth.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import com.fasterxml.jackson.annotation.JsonFormat;
import java.util.Date;
import java.math.BigDecimal;

@Schema(name = "权限接口关联")
@Data
public class ResourceInterfaceDTO {

    @Schema(name = "id",description = "主键")
    private Long id;

    @Schema(name = "resourceId",description = "权限id")
    private Long resourceId;

    @Schema(name = "interfaceId",description = "接口id")
    private Long interfaceId;

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

}
