package com.gientech.ragcommon.qa.request;

import com.fasterxml.jackson.annotation.JsonFormat;
import com.gientech.ragcommon.qa.enmus.ApiKeyBizTypeEnums;
import com.gientech.ragcommon.qa.enmus.ApiKeyStatusEnums;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import org.checkerframework.checker.formatter.qual.Format;

import java.math.BigDecimal;
import java.util.Date;

@Schema(name = "保存apikey的信息请求参数")
@Data
public class SaveApiKeyInfoReq {

    @Schema(name = "targetId",description = "目标id")
    private Integer targetId;

    @Schema(name = "bizType",description = "业务类型 1:助手配置")
    private Integer bizType = ApiKeyBizTypeEnums.QA_HELPER.getCode();

    @Schema(name = "expireTime",description = "过期时间")
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss",timezone = "GMT+8")
    private Date expireTime;

}
