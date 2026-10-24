package com.gientech.tools.database.domain.repository.impl;

import cn.hutool.core.bean.BeanUtil;
import com.alibaba.excel.util.StringUtils;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.infrastructure.exception.BusinessException;
import com.gientech.tools.database.domain.entity.TLDatabase;
import com.gientech.tools.database.domain.mapper.TLDatabaseMapper;
import com.gientech.tools.database.domain.model.TLDatabaseDO;
import com.gientech.tools.database.domain.repository.TLDatabaseRepository;
import com.gientech.ragcommon.index.enmus.DataSourceTypeEnum;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.stereotype.Repository;

import java.util.Date;
import java.util.List;
import java.util.Objects;

@Repository
public class TLDatabaseRepositoryImpl extends ServiceImpl<TLDatabaseMapper, TLDatabaseDO> implements TLDatabaseRepository {

    @Autowired
    private TLDatabaseMapper tlDatabaseMapper;

    @Override
    public Boolean save(TLDatabase tlDatabase) {
        LambdaQueryWrapper<TLDatabaseDO> wrapper = Wrappers.lambdaQuery();
        wrapper.eq(TLDatabaseDO::getName, tlDatabase.getName());
        TLDatabaseDO one = getOne(wrapper);
        if (Objects.nonNull(one)) {
            throw new BusinessException(ErrCodeEnum.DB_EXISTS);
        }
        User user = UserContext.getUser();
        String userName = user.getUserName();
        tlDatabase.setGmtCreate(new Date());
        tlDatabase.setGmtModified(new Date());
        tlDatabase.setCreateBy(userName);
        tlDatabase.setUpdateBy(userName);

        TLDatabaseDO tlDatabaseDO = BeanUtil.copyProperties(tlDatabase, TLDatabaseDO.class);
        try {
            boolean save = save(tlDatabaseDO);
            tlDatabase.setId(tlDatabaseDO.getId());
            return save;
        } catch (DuplicateKeyException e) {
            log.error(e.getMessage(), e);
            throw new BusinessException(ErrCodeEnum.DB_EXISTS);
        }
    }

    @Override
    public Page<TLDatabase> page(DataSourceTypeEnum dataSourceTypeEnum, Long pageNo, Long pageSize, String fuzzyWord, String userName, Boolean includingCreator) {
        LambdaQueryWrapper<TLDatabaseDO> queryWrapper = new LambdaQueryWrapper<>();

        if (!DataSourceTypeEnum.All.equals(dataSourceTypeEnum)) {
            queryWrapper = queryWrapper.eq(TLDatabaseDO::getDatasourceType, dataSourceTypeEnum.getCode());
        }
        if (StringUtils.isNotBlank(userName)) {
            if (includingCreator) {
                queryWrapper.eq(TLDatabaseDO::getCreateBy, userName);
            } else {
                queryWrapper.ne(TLDatabaseDO::getCreateBy, userName);
            }

        }
        return pageByWrapper(queryWrapper, fuzzyWord, pageNo, pageSize);
    }

    private Page<TLDatabase> pageByWrapper(LambdaQueryWrapper<TLDatabaseDO> queryWrapper, String fuzzyWord, Long pageNo, Long pageSize) {
        if (fuzzyWord != null && !fuzzyWord.isEmpty()) {
            queryWrapper = queryWrapper.and(qw -> qw.like(TLDatabaseDO::getName, fuzzyWord).or().like(TLDatabaseDO::getDescription, fuzzyWord));
        }

        queryWrapper = queryWrapper.orderByDesc(TLDatabaseDO::getGmtCreate);

        Page<TLDatabaseDO> page = new Page<>(pageNo, pageSize);
        Page<TLDatabaseDO> pageResult = super.baseMapper.selectPage(page, queryWrapper);
        Page<TLDatabase> listPage = new Page<>();
        BeanUtil.copyProperties(pageResult, listPage);
        listPage.setRecords(BeanUtil.copyToList(pageResult.getRecords(), TLDatabase.class));
        return listPage;
    }

    @Override
    public Page<TLDatabase> pageByTargetIds(List<Long> targetIds, Long pageNo, Long pageSize, String fuzzyWord, Boolean includingCreator) {
        LambdaQueryWrapper<TLDatabaseDO> queryWrapper = new LambdaQueryWrapper<>();
        queryWrapper.in(TLDatabaseDO::getId, targetIds);
        if (!includingCreator) {
            queryWrapper.ne(TLDatabaseDO::getCreateBy, UserContext.getUser().getUserName());
        }
        return pageByWrapper(queryWrapper, fuzzyWord, pageNo, pageSize);
    }

    @Override
    public TLDatabase findById(Long id) {
        TLDatabaseDO tlDatabaseDO = super.baseMapper.selectById(id);
        return Objects.isNull(tlDatabaseDO) ? null : BeanUtil.copyProperties(tlDatabaseDO, TLDatabase.class);
    }

    @Override
    public Boolean updateById(TLDatabase tlDatabase) {
        Long id = tlDatabase.getId();
        if (null == id) throw new RuntimeException("主键参数必传");

        TLDatabase oldTLDatabase = findById(id);
        if (null == oldTLDatabase) throw new RuntimeException("主键参数查询出的对象为空");

        tlDatabase.setCreateBy(oldTLDatabase.getCreateBy());
        tlDatabase.setGmtCreate(oldTLDatabase.getGmtCreate());

        User user = UserContext.getUser();
        String userName = user.getUserName();
        tlDatabase.setGmtModified(new Date());
        tlDatabase.setUpdateBy(userName);

        TLDatabaseDO tlDatabaseDO = BeanUtil.copyProperties(tlDatabase, TLDatabaseDO.class);

        return super.updateById(tlDatabaseDO);
    }

    @Override
    public Integer getHighestPermission(Long databaseId, Long deptId, Long userId, String userName) {
        return tlDatabaseMapper.getHighestPermission(databaseId, deptId, userId, userName);
    }
}
