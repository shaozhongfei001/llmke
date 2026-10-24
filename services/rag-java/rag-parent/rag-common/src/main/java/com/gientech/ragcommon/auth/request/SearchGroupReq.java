package com.gientech.ragcommon.auth.request;

import lombok.Data;


@Data
public class SearchGroupReq {

    /**
     * 机构名称
     */
    private String name;

    /**
     * 第几页 默认值 1
     */
    private Long pageNo = 1L;

    /**
     * 每页大小 默认值 20
     */
    private Long pageSize = 20L;
}
