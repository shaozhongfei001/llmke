package com.gientech.ragauthservice.domain.entity;

import lombok.Data;

@Data
public class UserInfoExt {

    /**
     * 用户ID
     */
    private Long userId;

    /**
     * 用户登录名
     */
    private String userName;

    /**
     * 用户名
     */
    private String userRealname;

    /**
     * 部门
     */
    private String deptName;

    /**
     * 邮箱
     */
    private String userEmail;

    /**
     * 角色
     */
    private String roleNames;

    /**
     * 创建时间
     */
    private String gmtCreate;

    /**
     * 状态
     */
    private String status;
}
