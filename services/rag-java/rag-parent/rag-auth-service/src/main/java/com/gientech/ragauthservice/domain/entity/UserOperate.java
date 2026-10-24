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
public class UserOperate {

    private static final long serialVersionUID = 1L;

    /**
     * 主键
    */
    private Long id;

    /**
     * 创建时间
    */
    private Date gmtCreated;

    /**
     * 创建时间
    */
    private Date gmtModified;

    /**
     * 方法名称
    */
    private String name;

    /**
     * 方法url
    */
    private String url;

    /**
     * 接口请求开始时间
    */
    private Date startTime;

    /**
     * 接口请求结束时间

    */
    private Date endTime;

    /**
     * 用户id
    */
    private Long userId;

    /**
     * 用户名称
    */
    private String userName;

    /**
     * 参数
    */
    private String params;

    /**
     * ip
    */
    private String ip;

    /**
     * 接口是否请求成功 0 否  1是 默认值1
    */
    private Integer success;

}
