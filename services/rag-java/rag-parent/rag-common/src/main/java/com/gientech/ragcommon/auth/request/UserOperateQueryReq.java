package com.gientech.ragcommon.auth.request;

import lombok.Data;

/**
 * @Descrption:
 * @Author:liutaiyun
 * @Date:2024/12/24 11:43
 **/
@Data
public class UserOperateQueryReq {
    /**
     * 接口名称 / 操作人
     */
    private  String fuzzy;

    /**
     * 查询开始时间
     */
    private String start;

    /**
     * 查询结束时间
     */
    private String end;

    private Long pageNo = 1L;

    private Long pageSize = 10l;
}
