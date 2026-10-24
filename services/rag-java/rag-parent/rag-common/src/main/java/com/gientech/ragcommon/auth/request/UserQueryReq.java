package com.gientech.ragcommon.auth.request;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * @Desc
 * @Author ZhenPanHong
 * @Date 2025/3/26 14:11
 */
@Builder
@AllArgsConstructor
@NoArgsConstructor
@Data
public class UserQueryReq {

    /**
     * 用户名
     */
    private String userName;

    /**
     * 用户真实姓名
     */
    private String userRealname;

    /**
     * 用户状态（ 1启用 0禁用 -2离职）
     */
    private Integer status;

    /**
     * 起始时间
     */
    private String startTime;

    /**
     * 结束时间
     */
    private String endTime;

    /**
     * 排序字段
     */
    private Boolean orderByResignDate;

    /**
     * 页码
     */
    private Long pageNo = 1L;

    /**
     * 页大小
     */
    private Long pageSize = 20L;
}
