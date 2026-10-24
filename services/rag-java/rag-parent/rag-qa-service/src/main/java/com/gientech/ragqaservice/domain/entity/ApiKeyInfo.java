package com.gientech.ragqaservice.domain.entity;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import java.math.BigDecimal;
import java.util.Date;
import java.util.LinkedHashSet;

@AllArgsConstructor
@NoArgsConstructor
@Data
public class ApiKeyInfo {

    private static final long serialVersionUID = 1L;

    /**
     * 主键
    */
    private Long id;

    /**
     * apikey全局唯一
    */
    private String apiKey;

    /**
     * 目标id
    */
    private Integer targetId;

    /**
     * 状态 0:禁用；1:正常 默认值1
    */
    private Integer status;

    /**
     * 业务类型 1:助手配置
    */
    private Integer bizType;

    /**
     * 过期时间
    */
    private Date expireTime;

    /**
     * 是否删除 -1 删除  1 正常 默认值1
    */
    private Integer isDel;

    /**
     * 创建人
    */
    private String createBy;

    /**
     * 创建时间
    */
    private Date gmtCreate;

    /**
     * 修改人
    */
    private String modifyBy;

    /**
     * 修改时间
    */
    private Date gmtModified;

}
