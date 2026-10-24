package com.gientech.ragauthservice.domain.entity;

import lombok.Data;

import java.io.Serializable;
import java.util.Date;

/**
 * <p>
 * 角色表
 * </p>
 *
 * @author wudf
 * @since 2024-06-26
 */
@Data
public class RoleInfo implements Serializable {

    /**
     * 逻辑删除 是否删除 1是 0否
     */
    private String isDtl;

    /**
     * 创建人
     */
    private String createBy;

    /**
     * 创建时间
     */
    private Date gmtCreate;

    /**
     * 更新人
     */
    private String updateBy;

    /**
     * 更新时间
     */
    private Date gmtModified;

    /**
     * 主键
     */
    private Long id;

    /**
     * 角色名称
     */
    private String name;

    /**
     * 描述
     */
    private String description;

    /**
     * 排序
     */
    private Long seq;

    /**
     * 状态 0 禁用 1 启用
     */
    private Integer status;
}
