package com.gientech.ragcommon.auth.dto;

import lombok.Data;

import java.util.List;

/**
 * @Desc 部门-数据权限关联 DTO类
 * @Author ZhenPanHong
 * @Date 2025/3/11 15:27
 */
@Data
public class DeptPrivilegeDTO {

    /**
     * id
     */
    private Long id;

    /**
     * 部门名
     */
    private String deptName;

    /**
     * 目标id
     */

    private Long targetId;

    /**
     * 部门id
     */
    private Long deptId;

    /**
     * 1:知识库;2:检索配置;3:模型
     */
    private Integer bizType;

    /**
     * 0:无任何权限, 1: 读权限，2: 读写权限, 3: 所有权限
     */
    private Integer permission;

    /**
     * 成员数量
     */
    private Long userCount;

    /**
     * 子部门权限列表
     */
    private List<DeptPrivilegeDTO> subDeptPrivilegeList;
}
