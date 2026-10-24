package com.gientech.ragauthservice.domain.entity;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.math.BigDecimal;
import java.util.Date;
import java.util.LinkedHashSet;

@AllArgsConstructor
@NoArgsConstructor
@Data
public class DepartmentInfo {

    private static final long serialVersionUID = 1L;

    /**
     * 主键
    */
    private Long id;

    /**
     * 部门名称
    */
    private String name;

    /**
     * 部门编码
    */
    private String code;

    /**
     * 部门管理员
    */
    private String admin;

    /**
     * 上级部门ID
    */
    private Long parentId;

    private String parentDeptName;

    private Integer userCount;

    /**
     * 状态：0:待激活；1:正常（已激活）；-1:删除
    */
    private Integer status;

    /**
     * 创建时间
    */
    private Date gmtCreate;

    /**
     * 修改时间
    */
    private Date gmtModified;

    /**
     * 创建人
    */
    private String createBy;

    /**
     * 修改人
    */
    private String modifyBy;

}
