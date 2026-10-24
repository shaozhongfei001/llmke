package com.gientech.sensitivewordsservice.domain.repository.impl;


import cn.hutool.core.bean.BeanUtil;
import com.alibaba.nacos.common.utils.CollectionUtils;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.toolkit.StringUtils;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.gientech.sensitivewordsservice.domain.convertor.SensitiveWordsConvertor;
import com.gientech.sensitivewordsservice.domain.entity.SensitiveWords;
import com.gientech.sensitivewordsservice.domain.mapper.SensitiveWordsMapper;
import com.gientech.sensitivewordsservice.domain.model.SensitiveWordsDO;
import com.gientech.sensitivewordsservice.domain.repository.SensitiveWordsRepository;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;

/**
 * <p>
 *  服务实现类
 * </p>
 *
 * @author wxc
 * @since 2024-08-13
 */
@Service
public class SensitiveWordsRepositoryImpl extends ServiceImpl<SensitiveWordsMapper, SensitiveWordsDO> implements SensitiveWordsRepository {

    @Override
    public Long add(SensitiveWords sensitiveWords) {
        SensitiveWordsDO sensitiveWordsDO = BeanUtil.copyProperties(sensitiveWords, SensitiveWordsDO.class);
        super.save(sensitiveWordsDO);
        return sensitiveWordsDO.getId();
    }

    @Override
    public Boolean updateById(SensitiveWords sensitiveWords) {
        SensitiveWordsDO sensitiveWordsDO = BeanUtil.copyProperties(sensitiveWords, SensitiveWordsDO.class);
        return super.updateById(sensitiveWordsDO);
    }

    @Override
    public SensitiveWords getById(Long id) {
        LambdaQueryWrapper<SensitiveWordsDO>  wrapper = Wrappers.lambdaQuery(SensitiveWordsDO.class);
        wrapper.ne(SensitiveWordsDO::getStatus,-1) //逻辑删除的记录不返回
                .eq(SensitiveWordsDO::getId,id);
        SensitiveWordsDO sensitiveWordsDO = super.getOne(wrapper);
        return Objects.isNull(sensitiveWordsDO)?null:BeanUtil.copyProperties(sensitiveWordsDO, SensitiveWords.class);
    }

    /**
     * 查询没有被删除的记录
     * @param name 敏感词库名称
     * @return 敏感词库
     */
    @Override
    public SensitiveWords getByName(String name) {
        LambdaQueryWrapper<SensitiveWordsDO>  wrapper = Wrappers.lambdaQuery(SensitiveWordsDO.class);
        wrapper.ne(SensitiveWordsDO::getStatus,-1) //逻辑删除的记录不返回
                .eq(SensitiveWordsDO::getName,name);
        SensitiveWordsDO sensitiveWordsDO = super.getOne(wrapper);
        return Objects.isNull(sensitiveWordsDO)?null:BeanUtil.copyProperties(sensitiveWordsDO, SensitiveWords.class);
    }

    @Override
    public Page<SensitiveWords> page(String name, List<Long> ids, Integer pageNo, Integer pageSize) {
        LambdaQueryWrapper<SensitiveWordsDO> wrapper = Wrappers.lambdaQuery(SensitiveWordsDO.class)
                .like(StringUtils.isNotBlank(name),SensitiveWordsDO::getName,name)
                .ne(SensitiveWordsDO::getStatus,-1)
                .in(CollectionUtils.isNotEmpty(ids),SensitiveWordsDO::getId,ids)
                .orderByDesc(SensitiveWordsDO::getGmtModified);

        //mybatis-plus分页
        Page<SensitiveWordsDO> page = new Page<>(pageNo, pageSize);
        super.page(page, wrapper);
        //
        Page<SensitiveWords> pageResult = new Page<>();
        BeanUtil.copyProperties(page,pageResult);
        pageResult.setRecords(BeanUtil.copyToList(page.getRecords(), SensitiveWords.class));
        return pageResult;
    }

    @Override
    public List<SensitiveWords> getListByIds(List<Long> ids) {
        if(CollectionUtils.isEmpty(ids)){
            return null;
        }
        return BeanUtil.copyToList(listByIds(ids), SensitiveWords.class);
//        return SensitiveWordsConvertor.INSTANCE.wordsDOList2WordsList(listByIds(ids));
    }
}
