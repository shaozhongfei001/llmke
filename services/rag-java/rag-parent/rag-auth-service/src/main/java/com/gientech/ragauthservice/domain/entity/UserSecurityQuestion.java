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
public class UserSecurityQuestion {

    private static final long serialVersionUID = 1L;

    /**
     * 主键编号
    */
    private Long id;

    /**
     * 用户编号
    */
    private Long userId;

    /**
     * 问题
    */
    private String question;

    /**
     * 答案
    */
    private String answer;

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
