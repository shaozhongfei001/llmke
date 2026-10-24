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
public class InterfaceInfo {

    private static final long serialVersionUID = 1L;

    /**
     * 主键
    */
    private Long id;

    /**
     * 应用名称
    */
    private String appName;

    /**
     * 应用简称
     */
    private String appNameAbbreviate;

    /**
     * 接口名称
    */
    private String name;

    /**
     * url
    */
    private String url;

    /**
     * 接口的请求方式
    */
    private String method;

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


    private Long resourceId;

    private String resourceName;

    private Integer resourceType;

}
