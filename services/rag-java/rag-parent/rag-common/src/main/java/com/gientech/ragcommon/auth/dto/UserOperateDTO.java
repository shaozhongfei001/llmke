package com.gientech.ragcommon.auth.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;
import com.fasterxml.jackson.annotation.JsonFormat;
import java.util.Date;
import java.math.BigDecimal;

@Schema(name = "用户操作更新")
@Data
public class UserOperateDTO {

    @Schema(name = "id",description = "主键")
    private Long id;

    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss",timezone = "GMT+8")
    @Schema(name = "gmtCreated",description = "创建时间")
    private Date gmtCreated;

    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss",timezone = "GMT+8")
    @Schema(name = "gmtModified",description = "创建时间")
    private Date gmtModified;

    @Schema(name = "name",description = "方法名称")
    private String name;

    @Schema(name = "url",description = "方法url")
    private String url;

    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss",timezone = "GMT+8")
    @Schema(name = "startTime",description = "接口请求开始时间")
    private Date startTime;

    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss",timezone = "GMT+8")
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
