package com.gientech.ragcommon.auth.dto;

import lombok.Data;

import java.io.Serializable;

@Data
public class UserPrivilegeDTO implements Serializable {

    /**
     * id
     */
    private Long id;

    /**
     * 配置id
     */
    private Long targetId;

    /**
     * 用户id
     */
    private Long userId;

    /**
     * 用户名称
     */
    private String userName;

    /**
     * 用户真实姓名
     */
    private String userRealname;

    /**
     * 1:知识库;2:检索配置;3:模型
     */
    private Integer bizType;

    /**
     * 0:无任何权限, 1: 读权限，2: 读写权限, 3: 所有权限
     */
    private Integer permission;

    /**
     * 部门名称
     */
    private String deptName;
}
