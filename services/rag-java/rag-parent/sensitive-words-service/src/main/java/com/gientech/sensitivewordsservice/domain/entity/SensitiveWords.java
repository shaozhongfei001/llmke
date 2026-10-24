package com.gientech.sensitivewordsservice.domain.entity;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;
import org.springframework.util.CollectionUtils;

import java.util.Date;
import java.util.LinkedHashSet;
import java.util.stream.Collectors;

@AllArgsConstructor
@NoArgsConstructor
@Data
public class SensitiveWords {
    /**
     * 主键
     */
    private Long id;

    /**
     * 创建时间
     */
    private Date gmtCreate;

    /**
     * 修改时间
     */
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
     * 状态，1正常，-1删除
     */
    private Integer status;

    /**
     * 敏感词位置
     */
    private Integer end;


    /**
     * 第几页
     */
    private Integer pageNo;

    /**
     * 每页大小
     */
    private Integer pageSize;

    public SensitiveWords(String name,Integer pageNo,Integer pageSize){
        this.name = name;
        this.pageNo = pageNo;
        this.pageSize = pageSize;
    }

    /**
     * 限制返回的敏感词个数
     * @param wordsCount 个数
     */
    public void wordCountLimit(int wordsCount) {
        if (this.words != null && this.words.size() > wordsCount) {
            this.words = new LinkedHashSet<>(this.words.stream().limit(wordsCount).collect(Collectors.toList()));
        }
    }


    /**
     * 敏感词数量：前端统计展示
     */
    private Integer count;


    public void setTotalCount() {
        this.count = CollectionUtils.isEmpty(words) ? 0 : words.size();
    }

}
