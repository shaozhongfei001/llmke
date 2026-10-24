package com.gientech.ragauthservice.domain.entity;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.util.Date;

/**
 * <p>
 * 用户表
 * </p>
 *
 * @author wudf
 * @since 2024-06-13
 */
@Data
@Builder
@AllArgsConstructor
@NoArgsConstructor
public class UserInfo implements Serializable {

    /**
     * 主键
     */
    private Long id;

    /**
     * 用户名
     */
    private String userName;

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

    /**
     * 逻辑删除 是否删除 1是 0 未删除
     */
    private String isDtl;

    /**
     * 密码
     */
    private String userPassword;

    /**
     * 真实姓名
     */
    private String userRealname;

    /**
     * 邮箱
     */
    private String userEmail;

    /**
     * 用户头像
     */
    private String url;

    /**
     * 手机
     */
    private String userPhone;

    /**
     * 状态  1启用 0禁用
     */
    private Integer status;

    /**
     * 过期时间
     */
    private Date expireTime;

    /**
     * 密码错误次数
     */
    private Integer missNum;

    /**
     * 密码更改时间
     */
    private Date passwordUpdated;

    /**
     * 管理员重置的密码
     */
    private String adminResetPassword;

    /**
     * ip
     */
    private String ip;

    /**
     * 上线时间
     */
    private Date onlineTime;

    /**
     * 机构id
     */
    private Long organizationId;

    /**
     * 用户工号
     */
    private String empNo;

    /**
     * 用户token的信息
     */
    private String token;

    /**
     * 部门id
     */
    private String deptId;

    /**
     * 角色id
     */
    private Long roleId;

    /**
     * 部门名称
     */
    private String deptName;

    /**
     * 认证key
     */
    private String appKey;


    /**
     * 离职日期
     */
    private Date resignDate;


    private String feature;

    /**
     * 用户来源
     */
    private Integer systemSource;

    /**
     * 是否已经完成密保问题的设置
     */
    private Boolean hasSetSecurityQuestion;
}
