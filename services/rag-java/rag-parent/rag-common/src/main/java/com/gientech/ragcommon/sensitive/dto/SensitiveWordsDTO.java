package com.gientech.ragcommon.sensitive.dto;


import com.fasterxml.jackson.annotation.JsonFormat;
import lombok.Data;

import java.io.Serializable;
import java.util.Date;
import java.util.Iterator;
import java.util.LinkedHashSet;
import java.util.Objects;

/**
 * <p>
 *
 * </p>
 *
 * @author wxc
 * @since 2024-08-13
 */
@Data
public class SensitiveWordsDTO implements Serializable {

    /**
     * 主键
     */
    private Long id;

    /**
     * 创建时间
     */
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss", timezone = "GMT+8")
    private Date gmtCreate;

    /**
     * 修改时间
     */
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss", timezone = "GMT+8")
    private Date gmtModified;

    /**
     * 敏感词库名称
     */
    private String name;

    /**
     * 描述
     */
    private String descript;

    /**
     * 敏感词详情
     */
    private LinkedHashSet<String> words;

    /**
     * 敏感词数量
     */
    private Integer count;

    /**
     * 状态，1正常，-1删除
     */
    private Integer status;

    /**
     * 敏感词位置
     */
    private Integer end;

    private Integer totalPage;

    private Integer currentPage;


    public void setPageParam(Integer total, Integer pageNo, Integer pageSize) {
        this.totalPage = total % pageSize == 0 ? total / pageSize : total / pageSize + 1;
        this.currentPage = pageNo;
        this.count = total;
        if (this.currentPage.equals(this.totalPage) && this.totalPage > 1) {
            int currentCount = total % pageSize;
            int deleteCount = pageSize - currentCount;
            if (Objects.nonNull(this.words) && !this.words.isEmpty()) {
                Iterator<String> iterator = this.words.iterator();
                while (iterator.hasNext() && deleteCount > 0) {
                    iterator.next();
                    iterator.remove();
                    deleteCount--;
                }
            }

        }
    }


}
