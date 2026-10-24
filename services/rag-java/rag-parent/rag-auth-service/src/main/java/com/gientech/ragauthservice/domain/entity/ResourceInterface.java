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
public class ResourceInterface {

    private static final long serialVersionUID = 1L;

    /**
     * 主键
    */
    private Long id;

    /**
     * 权限id
    */
    private Long resourceId;

    /**
     * 接口id
    */
    private Long interfaceId;

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

}
