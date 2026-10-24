package com.gientech.ragauthservice.domain.entity;

import lombok.Data;

import java.util.Date;
import java.util.List;

/**
 * @Desc 部门权限关系
 * @Author ZhenPanHong
 * @Date 2025/3/11 15:15
 */
@Data
public class DeptPrivilege {

    /**
     * id
     */
    private Long id;

    /**
     * 目标id
     */
    private Long targetId;


    private List<Long> targetIds;

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
     * 创建时间
     */
    private Date gmtCreate;

    /**
     * 更新时间
     */
    private Date gmtModified;

    /**
     * 创建人
     */
    private String createBy;

    /**
     * 更新人
     */
    private String updateBy;
}
