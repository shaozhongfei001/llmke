package com.gientech.ragcommon.auth.request;

import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * @Desc 部门权限更新
 * @Author ZhenPanHong
 * @Date 2025/3/11 15:11
 */
@Data
@Builder
@AllArgsConstructor
@NoArgsConstructor
public class DeptPermissionReq {

    /**
     * 部门id
     */
    @NotNull(message = "deptId不能为空")
    private Long deptId;

    /**
     * 目标id
     */
    @NotNull(message = "targetId不能为空")
    private Long targetId;

    /**
     * 业务类型 1:知识库;2:检索配置;3:模型
     */
    @NotNull(message = "bizType不能为空")
    private Integer bizType;

    /**
     * 0:无任何权限, 1: 读权限，2: 读写权限, 3: 所有权限
     */
    @NotNull(message = "permission不能为空")
    private Integer permission;

    private boolean withUser;
}
