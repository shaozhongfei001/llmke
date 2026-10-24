package com.gientech.ragcommon.auth.request;

import jakarta.validation.constraints.NotNull;
import lombok.Data;

import java.util.List;

/**
 * @Desc 部门权限更新
 * @Author ZhenPanHong
 * @Date 2025/3/11 15:11
 */
@Data
public class UpdateDeptPermissionReq {

    /**
     * 部门id
     */
    @NotNull(message = "deptId不能为空")
    private Long deptId;


    private List<Long> deptIds;

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
}
