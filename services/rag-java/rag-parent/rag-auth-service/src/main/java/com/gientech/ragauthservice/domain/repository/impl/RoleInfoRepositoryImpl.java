package com.gientech.ragauthservice.domain.repository.impl;

import cn.hutool.core.bean.BeanUtil;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragauthservice.domain.entity.RoleInfo;
import com.gientech.ragauthservice.domain.entity.UserInfo;
import com.gientech.ragauthservice.domain.mapper.RoleInfoMapper;
import com.gientech.ragauthservice.domain.model.RoleInfoDO;
import com.gientech.ragauthservice.domain.model.UserInfoDO;
import com.gientech.ragauthservice.domain.repository.RoleInfoRepository;
import com.gientech.ragcommon.auth.enums.IsDtlEnums;
import com.gientech.ragcommon.auth.enums.StatusEnums;
import com.gientech.ragcommon.auth.enums.UserIsDelEnum;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import com.google.common.collect.Lists;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Bean;
import org.springframework.stereotype.Repository;
import org.springframework.util.CollectionUtils;

import java.util.Date;
import java.util.List;
import java.util.Objects;

@Repository
public class RoleInfoRepositoryImpl implements RoleInfoRepository {

    @Autowired
    private RoleInfoMapper roleInfoMapper;

    @Override
    public RoleInfo queryByName(String roleName) {
        QueryWrapper<RoleInfoDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("name",roleName)
                .eq("is_dtl", IsDtlEnums.NO.getCode())
                .last("limit 1");
        RoleInfoDO roleInfoDO = roleInfoMapper.selectOne(queryWrapper);
        return Objects.isNull(roleInfoDO) ? null : BeanUtil.copyProperties(roleInfoDO,RoleInfo.class);
    }

    @Override
    public Boolean addRole(RoleInfo roleInfo) {
        User user = UserContext.getUser();
        String userName = user.getUserName();
        roleInfo.setCreateBy(userName);
        roleInfo.setGmtCreate(new Date());
        roleInfo.setUpdateBy(userName);
        roleInfo.setGmtModified(new Date());
        roleInfo.setIsDtl(IsDtlEnums.NO.getCode());
        roleInfo.setStatus(StatusEnums.ENABLED.getCode());
        RoleInfoDO roleInfoDO = BeanUtil.copyProperties(roleInfo, RoleInfoDO.class);
        Boolean result = roleInfoMapper.insert(roleInfoDO) > 0;
        roleInfo.setId(roleInfoDO.getId());
        return  result;
    }

    @Override
    public boolean updateRole(RoleInfo roleInfo) {
        roleInfo.setGmtModified(new Date());
        roleInfo.setUpdateBy(UserContext.getUser().getUserName());
        return roleInfoMapper.updateById(BeanUtil.copyProperties(roleInfo,RoleInfoDO.class)) > 0;
    }

    @Override
    public Page<RoleInfo> list(String idOrName, Integer status, Long pageNo, Long pageSize) {
        QueryWrapper<RoleInfoDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("is_dtl", IsDtlEnums.NO.getCode());
        if(!Objects.isNull(status)){
            queryWrapper.eq("status",status);
        }
        if(StringUtils.isNotBlank(idOrName)){
            queryWrapper
                    .and(name->name
                            .like("id",idOrName)
                            .or(id->id.like("name",idOrName)));
        }
        queryWrapper.orderByDesc("gmt_create");
        Page<RoleInfoDO> page = new Page<>(pageNo,pageSize);
        Page<RoleInfoDO> pageResult = roleInfoMapper.selectPage(page, queryWrapper);
        Page<RoleInfo> roleInfoPage = new Page<>();
        BeanUtil.copyProperties(pageResult,roleInfoPage);
        return roleInfoPage;
    }

    @Override
    public List<RoleInfo> queryByIds(List<Long> roleIds) {
        if(CollectionUtils.isEmpty(roleIds))
            return null;
        QueryWrapper<RoleInfoDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.in("id",roleIds).eq("is_dtl", IsDtlEnums.NO.getCode());
        List<RoleInfoDO> roleInfoDOS = roleInfoMapper.selectList(queryWrapper);
        return CollectionUtils.isEmpty(roleInfoDOS) ? null : BeanUtil.copyToList(roleInfoDOS,RoleInfo.class);
    }

    @Override
    public RoleInfo queryById(Long roleId,String roleName) {
        if(roleId == null)
            return null;
        QueryWrapper<RoleInfoDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("id",roleId)
                .eq("name",roleName)
                .eq("is_dtl", IsDtlEnums.NO.getCode())
                .last("limit 1");
        RoleInfoDO roleInfoDO = roleInfoMapper.selectOne(queryWrapper);
        return Objects.isNull(roleInfoDO) ? null : BeanUtil.copyProperties(roleInfoDO,RoleInfo.class);
    }

    @Override
    public RoleInfo queryById(Long roleId) {
        if(roleId == null)
            return null;
        QueryWrapper<RoleInfoDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("id",roleId)
                .eq("is_dtl", IsDtlEnums.NO.getCode())
                .last("limit 1");
        RoleInfoDO roleInfoDO = roleInfoMapper.selectOne(queryWrapper);
        return Objects.isNull(roleInfoDO) ? null : BeanUtil.copyProperties(roleInfoDO,RoleInfo.class);
    }

    @Override
    public List<RoleInfo> listAll(){
        QueryWrapper<RoleInfoDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("is_dtl", IsDtlEnums.NO.getCode());
        queryWrapper.eq("status", StatusEnums.ENABLED.getCode());
        List<RoleInfoDO> roleInfoDOS = roleInfoMapper.selectList(queryWrapper);
        return CollectionUtils.isEmpty(roleInfoDOS) ? Lists.newArrayList() : BeanUtil.copyToList(roleInfoDOS,RoleInfo.class);
    }
}
