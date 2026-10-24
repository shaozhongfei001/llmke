package com.gientech.ragcommon.auth.request;

import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.util.List;

/**
 * @Desc 部门权限请求体
 * @Author ZhenPanHong
 * @Date 2025/3/11 15:06
 */
@Data
public class DeptPrivilegeReq {
    /**
     * 业务类型 1:知识库;2:检索配置;3:模型
     */
    @NotNull(message = "bizType不能为空")
    private Integer bizType;

    /**
     * 部门id
     */
    @NotEmpty(message = "deptIds不能为空")
    private List<Long> deptIds;

    /**
     * 目标id
     */
    @NotNull(message = "targetId不能为空")
    private Long targetId;

    /**
     * 0:无任何权限, 1: 读权限，2: 读写权限, 3: 所有权限
     */
    @NotNull(message = "permission不能为空")
    private Integer permission;
}
