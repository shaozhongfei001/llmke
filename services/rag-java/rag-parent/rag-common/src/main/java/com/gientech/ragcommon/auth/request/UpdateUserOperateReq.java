package com.gientech.ragcommon.auth.request;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import java.math.BigDecimal;
import java.util.Date;

@Schema(name = "更新请求参数")
@Data
public class UpdateUserOperateReq {

    @Schema(name = "id",description = "主键")
    private Long id;

    @Schema(name = "gmtCreated",description = "创建时间")
    private Date gmtCreated;

    @Schema(name = "name",description = "方法名称")
    private String name;

    @Schema(name = "url",description = "方法url")
    private String url;

    @Schema(name = "startTime",description = "接口请求开始时间")
    private Date startTime;

    @Schema(name = "endTime",description = "接口请求结束时间")
    private Date endTime;

    @Schema(name = "userId",description = "用户id")
    private Long userId;

    @Schema(name = "userName",description = "用户名称")
    private String userName;

    @Schema(name = "params",description = "参数")
    private String params;

    @Schema(name = "ip",description = "ip")
    private String ip;

    @Schema(name = "success",description = "接口是否请求成功 0 否  1是 默认值1")
    private Integer success;

}
