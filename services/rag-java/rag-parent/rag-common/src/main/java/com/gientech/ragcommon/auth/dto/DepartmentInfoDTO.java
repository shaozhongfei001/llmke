package com.gientech.ragcommon.auth.dto;

import com.fasterxml.jackson.annotation.JsonFormat;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Date;

@Schema(name = "")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class DepartmentInfoDTO {

    @Schema(name = "id", description = "主键")
    private Long id;

    @Schema(name = "name", description = "部门名称")
    private String name;

    @Schema(name = "code", description = "部门编码")
    private String code;

    @Schema(name = "admin", description = "部门管理员")
    private String admin;

    @Schema(name = "parentId", description = "上级部门ID")
    private Long parentId;

    @Schema(name = "status", description = "状态：0:待激活；1:正常（已激活）；-1:删除")
    private Integer status;

    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss", timezone = "GMT+8")
    @Schema(name = "gmtCreate", description = "创建时间")
    private Date gmtCreate;

    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss", timezone = "GMT+8")
    @Schema(name = "gmtModified", description = "修改时间")
    private Date gmtModified;

    @Schema(name = "createBy", description = "创建人")
    private String createBy;

    @Schema(name = "modifyBy", description = "修改人")
    private String modifyBy;

}
