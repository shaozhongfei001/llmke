package com.gientech.ragcommon.auth.dto;

import com.fasterxml.jackson.annotation.JsonFormat;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

import java.util.Date;

/**
 * @Desc 离职用户DTO
 * @Author ZhenPanHong
 * @Date 2025/3/21 15:19
 */
@Schema(name = "离职用户")
@Data
public class ResignedUserDTO {

    @Schema(name = "id", description = "用户名id")
    private Long id;

    @Schema(name = "userName", description = "用户登录名")
    private String userName;

    @Schema(name = "userRealname", description = "用户真实姓名")
    private String userRealname;

    @Schema(name = "userPhone", description = "用户手机号")
    private String userPhone;

    @Schema(name = "userEmail", description = "用户邮箱")
    private String userEmail;

    @Schema(name = "status", description = "用户状态（ 1启用 0禁用 -2离职）")
    private Integer status;

    @Schema(name = "resignDate", description = "离职日期")
    @JsonFormat(pattern = "yyyy-MM-dd", timezone = "GMT+8")
    private Date resignDate;

    @Schema(name = "resignedDays", description = "离职天数")
    private Long resignedDays;

    @Schema(name = "deptId", description = "部门id")
    private String deptId;

    @Schema(name = "deptName", description = "部门名称")
    private String deptName;
}
