package com.gientech.sensitivewordsservice.domain.mapper;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.core.toolkit.Constants;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.sensitivewordsservice.domain.model.SensitiveWordsDO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

/**
 * <p>
 * Mapper 接口
 * </p>
 *
 * @author wxc
 * @since 2024-08-13
 */
@Mapper
public interface SensitiveWordsMapper extends BaseMapper<SensitiveWordsDO> {
    SensitiveWordsDO queryWordsPageById(@Param("id") Long id, @Param("pageNo") Integer pageNo, @Param("pageSize") Integer pageSize);

    Page<SensitiveWordsDO> selectPageCustom(IPage<SensitiveWordsDO> page, @Param(Constants.WRAPPER) LambdaQueryWrapper<SensitiveWordsDO> wrapper);
}
