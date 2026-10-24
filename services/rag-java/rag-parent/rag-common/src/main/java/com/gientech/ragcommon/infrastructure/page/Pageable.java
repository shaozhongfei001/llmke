package com.gientech.ragcommon.infrastructure.page;

import lombok.Data;

import java.util.List;

/**
 * @Descrption: Pageable
 * @Author:xzj
 * @Date:2022/11/21 15:10
 **/
@Data
public class Pageable<T> {
    /**
     * 当前页码
     */
    private long pageNo;

    /**
     * 页面大小
     */
    private long pageSize;

    /**
     * 总页数
     */
    private long totalPage;

    /**
     * 总记录数
     */
    private long total;

    /**
     * 返回数据
     */
    private List<T> dataList;

    public static <T> Pageable of(long pageNo, long pageSize, long total, List<T> dataList) {
        Pageable pageable = new Pageable();
        pageable.setPageNo(pageNo);
        pageable.setPageSize(pageSize);
        long totalPage = 0L;
        if (pageSize != 0L) {
            totalPage = (total + pageSize - 1) / pageSize;
        }
        pageable.setTotalPage(totalPage);
        pageable.setTotal(total);
        pageable.setDataList(dataList);
        return pageable;
    }
}
