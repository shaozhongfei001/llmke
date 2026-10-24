package com.gientech.ragauthservice.domain.entity;

import lombok.Data;

import java.io.Serializable;
import java.util.Date;

/**
 * <p>
 * 机构-用户关联表
 * </p>
 *
 * @author wudf
 * @since 2024-07-23
 */
@Data
public class UserGroup implements Serializable {

    private static final long serialVersionUID = 1L;

    /**
     * id
     */
    private Long id;

    /**
     * 用户id
     */
    private Long userId;

    /**
     * 机构分组id
     */
    private Long groupId;

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
     * 成员数量
     */
    private Long userCount;


    private Long deptId;
}
