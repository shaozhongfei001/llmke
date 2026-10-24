package com.gientech.ragcommon.auth.dto;

import com.alibaba.excel.util.StringUtils;
import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.databind.annotation.JsonSerialize;
import com.fasterxml.jackson.databind.ser.std.ToStringSerializer;
import io.swagger.v3.oas.annotations.media.Schema;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serial;
import java.io.Serializable;
import java.util.Date;
import java.util.List;
import java.util.Objects;

@Schema(name = "用户详情")
@Data
@AllArgsConstructor
@NoArgsConstructor
public class UserInfoDTO implements Serializable {

    @Serial
    private static final long serialVersionUID = 1040323082224886916L;

    @JsonSerialize(using = ToStringSerializer.class)
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

    @Schema(name = "userEmail", description = "用户头像url")
    private String url;

    @Schema(name = "status", description = "用户状态（ 1启用 0禁用）")
    private Integer status;

    @Schema(name = "token", description = "登录token")
    private String token;

    @Schema(name = "gmtCreate", description = "创建时间")
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss", timezone = "GMT+8")
    private Date gmtCreate;

    @Schema(name = "userPassword", description = "密码")
    private String userPassword;

    @Schema(name = "deptId", description = "部门id")
    private String deptId;

    @Schema(name = "deptName", description = "部门名称")
    private String deptName;

    @Schema(name = "roles", description = "角色信息")
    private List<RoleInfoDTO> roles;

    @Schema(name = "userType", description = "用户类型 1 超级管理员")
    private Integer userType;

    @Schema(name = "feature", description = "用户特征")
    private String feature;

    @Schema(name = "systemSource", description = "用户来源")
    private Integer systemSource;

    @Schema(name = "hasSetSecurityQuestion", description = "是否设置密保问题")
    private Boolean hasSetSecurityQuestion;

    @Schema(name = "hasAdminResetPassword", description = "管理员是否重置密码")
    private Boolean hasAdminResetPassword;

    @Schema(name = "appKey",description = "appKey")
    private String appKey;


    public Long getLongTypeDeptId() {
        Long deptId = null;
        if (StringUtils.isNotBlank(this.deptId)) {
            deptId = Long.valueOf(this.deptId);
        }
        return deptId;
    }


    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        UserInfoDTO that = (UserInfoDTO) o;
        return Objects.equals(id, that.id) && Objects.equals(userName, that.userName);
    }

    @Override
    public int hashCode() {
        return Objects.hash(id, userName);
    }
}
