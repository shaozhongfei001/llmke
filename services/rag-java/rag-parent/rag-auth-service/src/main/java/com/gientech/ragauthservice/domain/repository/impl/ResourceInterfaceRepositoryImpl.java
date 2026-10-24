package com.gientech.ragauthservice.domain.repository.impl;

import cn.hutool.core.bean.BeanUtil;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragauthservice.domain.model.ResourceInfoDO;
import com.gientech.ragcommon.auth.enums.ResInterIsDelEnums;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragauthservice.domain.entity.ResourceInterface;
import com.gientech.ragauthservice.domain.mapper.ResourceInterfaceMapper;
import com.gientech.ragauthservice.domain.model.ResourceInterfaceDO;
import com.gientech.ragauthservice.domain.repository.ResourceInterfaceRepository;
import com.google.common.collect.Lists;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;
import org.springframework.util.CollectionUtils;

import java.util.Date;
import java.util.List;
import java.util.Objects;

@Repository
public class  ResourceInterfaceRepositoryImpl implements  ResourceInterfaceRepository {

    @Autowired
    private  ResourceInterfaceMapper  resourceInterfaceMapper;

    @Override
    public ResourceInterface findById(Long id) {
        QueryWrapper<ResourceInterfaceDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("id",id)
                .eq("is_del", ResInterIsDelEnums.NO.getCode())
                .last("limit 1");
        ResourceInterfaceDO resourceInterfaceDO = resourceInterfaceMapper.selectById(id);
        return Objects.isNull(resourceInterfaceDO) ? null : BeanUtil.copyProperties(resourceInterfaceDO,ResourceInterface.class);
    }

    @Override
    public Boolean save(ResourceInterface resourceInterface) {
        User user = UserContext.getUser();
        String userName = user.getUserName();
        resourceInterface.setUpdateBy(userName);
        resourceInterface.setCreateBy(userName);
        resourceInterface.setGmtCreate(new Date());
        resourceInterface.setGmtModified(resourceInterface.getGmtCreate());
        return resourceInterfaceMapper.insert(BeanUtil.copyProperties(resourceInterface, ResourceInterfaceDO.class)) > 0;
    }

    @Override
    public Boolean updateById(ResourceInterface resourceInterface) {
        if (Objects.isNull(resourceInterface.getId()))
            return false;
        User user = UserContext.getUser();
        String userName = user.getUserName();
        resourceInterface.setUpdateBy(userName);
        resourceInterface.setGmtModified(new Date());
        return resourceInterfaceMapper.updateById(BeanUtil.copyProperties(resourceInterface, ResourceInterfaceDO.class)) > 0;
    }

    @Override
    public Page<ResourceInterface> list(Long pageNo, Long pageSize) {
        QueryWrapper<ResourceInterfaceDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("is_del",ResInterIsDelEnums.NO.getCode())
                .orderByDesc("gmt_create");
        Page<ResourceInterfaceDO> page = new Page<>(pageNo, pageSize);
        Page<ResourceInterfaceDO> pageResult = resourceInterfaceMapper.selectPage(page, queryWrapper);
        Page<ResourceInterface> listPage = new Page<>();
        BeanUtil.copyProperties(pageResult,listPage);
        listPage.setRecords(BeanUtil.copyToList(pageResult.getRecords(),ResourceInterface.class));
        return listPage;
    }

    @Override
    public Boolean deleteById(Long id) {
        if(Objects.isNull(id))
            return false;
        ResourceInterfaceDO resourceInterfaceDO = new ResourceInterfaceDO();
        resourceInterfaceDO.setId(id);
        resourceInterfaceDO.setIsDel(ResInterIsDelEnums.YES.getCode());
        return resourceInterfaceMapper.deleteById(id) > 0;
    }

    @Override
    public List<ResourceInterface> findByResourceIds(List<Long> resourceIds) {
        if(CollectionUtils.isEmpty(resourceIds))
            return Lists.newArrayList();
        QueryWrapper<ResourceInterfaceDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.in("resource_id",resourceIds)
                .eq("is_del",ResInterIsDelEnums.NO.getCode());
        List<ResourceInterfaceDO> resourceInterfaceDOS = resourceInterfaceMapper.selectList(queryWrapper);
        return CollectionUtils.isEmpty(resourceInterfaceDOS) ? Lists.newArrayList() : BeanUtil.copyToList(resourceInterfaceDOS,ResourceInterface.class);
    }
}
