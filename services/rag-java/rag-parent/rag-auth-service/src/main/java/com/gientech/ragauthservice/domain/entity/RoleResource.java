package com.gientech.ragauthservice.domain.entity;

import lombok.Data;
import java.util.Date;

/**
 * <p>
 * 角色-资源关系表
 * </p>
 *
 * @author wudf
 * @since 2024-06-27
 */
@Data
public class RoleResource {


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
     * 角色id
     */
    private Long roleId;

    /**
     * 资源id
     */
    private Long resourceId;

    /**
     * 状态（1:启用; 0:禁用）
     */
    private Integer status;
}
