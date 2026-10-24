package com.gientech.ragauthservice.domain.entity;

import lombok.Data;

import java.util.Date;

@Data
public class ResourceInfo {

    /**
     * 逻辑删除 是否删除 1是 0否
     */
    private String isDtl;

    /**
     * 创建时间
     */
    private Date gmtCreate;

    /**
     * 创建人
     */
    private String createBy;

    /**
     * 修改时间
     */
    private Date gmtModified;

    /**
     * 更新人
     */
    private String updateBy;

    /**
     * 主键
     */
    private Long id;

    /**
     * 名称
     */
    private String name;

    /**
     * 路径
     */
    private String url;

    /**
     * 描述
     */
    private String description;

    /**
     * 图标
     */
    private String icon;

    /**
     * 父类id
     */
    private Long pid;

    /**
     * 排序
     */
    private Long seq;

    /**
     * 状态 0 禁用 1 启用
     */
    private Integer status;

    /**
     * 菜单类型 1:菜单;2:接口
     */
    private Integer resourceType;

    /**
     * 编码
     */
    private String code;

    private Long resourceId;
}
