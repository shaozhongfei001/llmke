package com.gientech.ragauthservice.domain.model;

import lombok.Data;

import java.util.Date;

@Data
public class ResourceInfoWithVisibleDO {

    private Long id;

    private String isDtl;

    private Date gmtCreate;

    private String createBy;

    private Date gmtModified;

    private String updateBy;

    private String name;

    private String url;

    private String description;

    private String icon;

    private Long pid;

    private Long seq;

    private Integer status;

    private String type;

    private String resourceType;

    private String serviceName;

    private String subType;

    private String code;

    private Long resourceId;
}