package com.gientech.ragcommon.auth.request;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import java.math.BigDecimal;
import java.util.Date;

@Schema(name = "保存权限接口关联请求参数")
@Data
public class SaveResourceInterfaceReq {

    @Schema(name = "resourceId",description = "权限id")
    private Long resourceId;

    @Schema(name = "interfaceId",description = "接口id")
    private Long interfaceId;

}
