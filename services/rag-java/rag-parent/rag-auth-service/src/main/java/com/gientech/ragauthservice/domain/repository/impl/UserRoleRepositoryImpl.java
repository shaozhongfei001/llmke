package com.gientech.ragauthservice.domain.repository.impl;


import cn.hutool.core.bean.BeanUtil;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.gientech.ragauthservice.domain.entity.UserRole;
import com.gientech.ragauthservice.domain.mapper.UserRoleMapper;
import com.gientech.ragauthservice.domain.model.UserRoleDO;
import com.gientech.ragauthservice.domain.repository.UserRoleRepository;
import com.gientech.ragcommon.auth.enums.IsDtlEnums;
import com.gientech.ragcommon.auth.enums.StatusEnums;
import com.gientech.ragcommon.auth.enums.UserStatusEnum;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Bean;
import org.springframework.stereotype.Repository;
import org.springframework.util.CollectionUtils;

import java.util.*;

@Repository
public class UserRoleRepositoryImpl implements UserRoleRepository {

    @Autowired
    private UserRoleMapper userRoleMapper;

    @Override
    public List<UserRole> queryByUserId(Long userId) {
        QueryWrapper<UserRoleDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("user_id",userId)
                .eq("is_dtl",IsDtlEnums.NO.getCode())
                .eq("status",1);
        List<UserRoleDO> userRoleDOS = userRoleMapper.selectList(queryWrapper);
        return CollectionUtils.isEmpty(userRoleDOS)?null: BeanUtil.copyToList(userRoleDOS,UserRole.class);
    }

    @Override
    public void addUserRoles(Long userId, List<Long> addRoleIds) {
        if(Objects.isNull(userId) || CollectionUtils.isEmpty(addRoleIds)){
            return;
        }
        User user = UserContext.getUser();
        String userName = user.getUserName();
        Date now = new Date();
        List<UserRoleDO> userRoleDOS = new ArrayList<>(addRoleIds.size());
        addRoleIds.forEach(roleId->{
            UserRoleDO userRoleDO = new UserRoleDO();
            userRoleDO.setIsDtl(IsDtlEnums.NO.getCode());
            userRoleDO.setGmtCreate(now);
            userRoleDO.setGmtModified(now);
            userRoleDO.setCreateBy(userName);
            userRoleDO.setUpdateBy(userName);
            userRoleDO.setRoleId(roleId);
            userRoleDO.setUserId(userId);
            userRoleDO.setStatus(StatusEnums.ENABLED.getCode());
            userRoleDOS.add(userRoleDO);
        });
        userRoleMapper.saveBatch(userRoleDOS);
    }

    @Override
    public void addUserRoles(List<UserRole> userRoles) {
        if(CollectionUtils.isEmpty(userRoles))
            return;
        User user = UserContext.getUser();
        String userName = user.getUserName();
        Date now = new Date();
        List<UserRoleDO> userRoleDOS = new ArrayList<>(userRoles.size());
        userRoles.forEach(userRole -> {
            UserRoleDO userRoleDO = new UserRoleDO();
            userRoleDO.setIsDtl(IsDtlEnums.NO.getCode());
            userRoleDO.setGmtCreate(now);
            userRoleDO.setGmtModified(now);
            userRoleDO.setCreateBy(userName);
            userRoleDO.setUpdateBy(userName);
            userRoleDO.setRoleId(userRole.getRoleId());
            userRoleDO.setUserId(userRole.getUserId());
            userRoleDO.setStatus(StatusEnums.ENABLED.getCode());
            userRoleDOS.add(userRoleDO);
        });
        userRoleMapper.saveBatch(userRoleDOS);
    }

    @Override
    public void delUserRoles(Long userId, List<Long> delRoleIds) {
        if(Objects.isNull(userId) || CollectionUtils.isEmpty(delRoleIds)){
            return;
        }
        QueryWrapper<UserRoleDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("user_id",userId);
        queryWrapper.in("role_id",delRoleIds);

        UserRoleDO userRoleDO = new UserRoleDO();
        userRoleDO.setIsDtl(IsDtlEnums.YES.getCode());
        userRoleMapper.update(userRoleDO,queryWrapper);
    }

    @Override
    public List<UserRole> queryByRoleId(Long roleId) {
        if(Objects.isNull(roleId)){
            return null;
        }
        QueryWrapper<UserRoleDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("role_id",roleId)
                .eq("is_dtl",IsDtlEnums.NO.getCode());
        List<UserRoleDO> userRoleDOS = userRoleMapper.selectList(queryWrapper);
        return CollectionUtils.isEmpty(userRoleDOS) ? null : BeanUtil.copyToList(userRoleDOS,UserRole.class);
    }

    @Override
    public void deleteByuserIds(List<Long> userIds) {
        if(CollectionUtils.isEmpty(userIds))
            return;
        QueryWrapper<UserRoleDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.in("user_id",userIds);

        UserRoleDO userRoleDO = new UserRoleDO();
        userRoleDO.setIsDtl(IsDtlEnums.YES.getCode());
        userRoleMapper.update(userRoleDO,queryWrapper);
    }

    @Override
    public void deleteByRoleAndUser(Long roleId, List<Long> userIds) {
        if(CollectionUtils.isEmpty(userIds) || Objects.isNull(roleId))
            return;
        QueryWrapper<UserRoleDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("role_id",roleId)
                .in("user_id",userIds);
        UserRoleDO userRoleDO = new UserRoleDO();
        userRoleDO.setIsDtl(IsDtlEnums.YES.getCode());
        userRoleMapper.update(userRoleDO,queryWrapper);
    }
}
