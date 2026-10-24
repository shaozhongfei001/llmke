package com.gientech.sensitivewordsservice.domain.repository;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.IService;
import com.gientech.sensitivewordsservice.domain.entity.SensitiveWords;
import com.gientech.sensitivewordsservice.domain.model.SensitiveWordsDO;

import java.util.List;

/**
 * <p>
 *  服务类
 * </p>
 *
 * @author wxc
 * @since 2024-08-13
 */
public interface SensitiveWordsRepository extends IService<SensitiveWordsDO>{

    Long add(SensitiveWords sensitiveWords);

    Boolean updateById(SensitiveWords sensitiveWords);

    /**
     * 查询没有被删除的记录
     * @param id 主键
     * @return 敏感词库
     */
    SensitiveWords getById(Long id);

    /**
     * 查询没有被删除的记录
     * @param name 敏感词库名称
     * @return 敏感词库
     */
    SensitiveWords getByName(String name);

    Page<SensitiveWords> page(String name, List<Long> ids, Integer pageNo, Integer pageSize);

    List<SensitiveWords> getListByIds(List<Long> ids);

}
