package com.gientech.ragauthservice.domain.repository.impl;

import cn.hutool.core.bean.BeanUtil;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragauthservice.domain.entity.InterfaceInfo;
import com.gientech.ragauthservice.domain.mapper.InterfaceInfoMapper;
import com.gientech.ragauthservice.domain.model.InterfaceInfoDO;
import com.gientech.ragauthservice.domain.repository.InterfaceInfoRepository;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import com.google.common.collect.Lists;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;
import org.springframework.util.CollectionUtils;

import java.util.Date;
import java.util.List;
import java.util.Objects;

@Repository
public class InterfaceInfoRepositoryImpl implements InterfaceInfoRepository {

    @Autowired
    private InterfaceInfoMapper interfaceInfoMapper;

    @Override
    public InterfaceInfo findById(Long id) {
        InterfaceInfoDO interfaceInfoDO = interfaceInfoMapper.selectById(id);
        return Objects.isNull(interfaceInfoDO) ? null : BeanUtil.copyProperties(interfaceInfoDO, InterfaceInfo.class);
    }

    @Override
    public Boolean save(InterfaceInfo interfaceInfo) {
        User user = UserContext.getUser();
        String userName = user.getUserName();
        interfaceInfo.setUpdateBy(userName);
        interfaceInfo.setCreateBy(userName);
        interfaceInfo.setGmtCreate(new Date());
        interfaceInfo.setGmtModified(interfaceInfo.getGmtCreate());
        return interfaceInfoMapper.insert(BeanUtil.copyProperties(interfaceInfo, InterfaceInfoDO.class)) > 0;
    }

    @Override
    public Boolean updateById(InterfaceInfo interfaceInfo) {
        if (Objects.isNull(interfaceInfo.getId()))
            return false;
        User user = UserContext.getUser();
        String userName = user.getUserName();
        interfaceInfo.setUpdateBy(userName);
        interfaceInfo.setGmtModified(new Date());
        return interfaceInfoMapper.updateById(BeanUtil.copyProperties(interfaceInfo, InterfaceInfoDO.class)) > 0;
    }

    @Override
    public Page<InterfaceInfo> list(Long pageNo, Long pageSize) {
        QueryWrapper<InterfaceInfoDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.orderByDesc("gmt_create");
        Page<InterfaceInfoDO> page = new Page<>(pageNo, pageSize);
        Page<InterfaceInfoDO> pageResult = interfaceInfoMapper.selectPage(page, queryWrapper);
        Page<InterfaceInfo> listPage = new Page<>();
        BeanUtil.copyProperties(pageResult, listPage);
        listPage.setRecords(BeanUtil.copyToList(pageResult.getRecords(), InterfaceInfo.class));
        return listPage;
    }

    @Override
    public Page<InterfaceInfo> listExtInterfaces(Long pageNo, Long pageSize, String fuzzy) {
        Page<InterfaceInfoDO> page = new Page<>(pageNo, pageSize);
        Page<InterfaceInfoDO> pageResult = interfaceInfoMapper.selectCustomPage(page, fuzzy);
        Page<InterfaceInfo> listPage = new Page<>();
        BeanUtil.copyProperties(pageResult, listPage);
        listPage.setRecords(BeanUtil.copyToList(pageResult.getRecords(), InterfaceInfo.class));
        return listPage;
    }

    @Override
    public Boolean deleteById(Long id) {
        return interfaceInfoMapper.deleteById(id) > 0;
    }

    @Override
    public List<InterfaceInfo> findByAppName(String appName) {
        if (StringUtils.isEmpty(appName))
            return Lists.newArrayList();
        QueryWrapper<InterfaceInfoDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("app_name", appName);
        List<InterfaceInfoDO> interfaceInfoDOS = interfaceInfoMapper.selectList(queryWrapper);
        return CollectionUtils.isEmpty(interfaceInfoDOS) ? Lists.newArrayList() : BeanUtil.copyToList(interfaceInfoDOS, InterfaceInfo.class);
    }

    @Override
    public int saveBatch(List<InterfaceInfo> needToInserts) {
        List<InterfaceInfoDO> interfaceInfoDOS = BeanUtil.copyToList(needToInserts, InterfaceInfoDO.class);
        return interfaceInfoMapper.saveBatch(interfaceInfoDOS);
    }

    @Override
    public Boolean deleteByAppName(String appName) {
        if (StringUtils.isEmpty(appName))
            return true;
        QueryWrapper<InterfaceInfoDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("app_name", appName);
        interfaceInfoMapper.delete(queryWrapper);
        return true;
    }

    @Override
    public List<InterfaceInfo> findByIds(List<Long> ids) {
        if (CollectionUtils.isEmpty(ids))
            return Lists.newArrayList();
        QueryWrapper<InterfaceInfoDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.in("id", ids);
        List<InterfaceInfoDO> interfaceInfoDOS = interfaceInfoMapper.selectList(queryWrapper);
        return CollectionUtils.isEmpty(interfaceInfoDOS) ? Lists.newArrayList() : BeanUtil.copyToList(interfaceInfoDOS, InterfaceInfo.class);
    }
}
