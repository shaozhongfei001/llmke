package com.gientech.ragauthservice.application.service.impl;

import cn.hutool.core.collection.CollectionUtil;
import com.gientech.ragauthservice.application.service.UserRoleAppService;
import com.gientech.ragauthservice.domain.entity.UserRole;
import com.gientech.ragauthservice.domain.service.UserRoleDomainService;
import com.gientech.ragcommon.auth.request.UserRoleUpdateReq;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.stream.Collectors;

@Service
public class UserRoleAppServiceImpl implements UserRoleAppService {

    @Autowired
    private UserRoleDomainService userRoleDomainService;

    private final Long adminId = 1000L;

    @Override
    public Boolean setRole(UserRoleUpdateReq userRoleUpdateReq) {
        Long userId = userRoleUpdateReq.getUserId();
        List<Long> roleIds = userRoleUpdateReq.getRoleIds();
        if (Objects.isNull(userId)) {
            throw new ApplicationException(ErrCodeEnum.USER_EMPTY);
        }
        if(adminId.equals(userId))
            throw new ApplicationException(ErrCodeEnum.USER_ADMIN_NO_UPDATE);
        updateUserRole(userId, roleIds);
        return true;
    }

    private void updateUserRole(Long userId, List<Long> roleIds) {
        List<UserRole> dbUserRoleList = userRoleDomainService.queryByUserId(userId);
        dbUserRoleList = CollectionUtils.isEmpty(dbUserRoleList) ? new ArrayList<>() : dbUserRoleList;
        List<Long> dbRoleIds = dbUserRoleList.stream().map(dbUserRole -> dbUserRole.getRoleId()).collect(Collectors.toList());
        List<Long> addRoleIds = (List<Long>) CollectionUtil.subtract(roleIds, dbRoleIds);
        List<Long> delRoleIds = (List<Long>) CollectionUtil.subtract(dbRoleIds, roleIds);
        userRoleDomainService.addUserRoles(userId, addRoleIds);
        userRoleDomainService.delUserRoles(userId, delRoleIds);
    }

    @Override
    public Boolean removeRole(Long userId, List<Long> roleIds) {
        userRoleDomainService.delUserRoles(userId, roleIds);
        return true;
    }

    @Override
    public Boolean setRoles(List<UserRoleUpdateReq> userRoleUpdateReqs) {
        userRoleUpdateReqs.forEach(item->setRole(item));
        return true;
    }

    @Override
    public Boolean setUserRole(UserRoleUpdateReq userRoleUpdateReq) {
        Long roleId = userRoleUpdateReq.getRoleId();
        List<Long> userIds = userRoleUpdateReq.getUserIds();
        if(Objects.isNull(roleId) || CollectionUtils.isEmpty(userIds))
            return false;
        List<UserRole> userRoles = new ArrayList<>();
        userIds.forEach(userId -> {
            UserRole userRole = new UserRole();
            userRole.setRoleId(roleId);
            userRole.setUserId(userId);
            userRoles.add(userRole);
        });
        userRoleDomainService.addUserRoles(userRoles);
        return true;
    }

    @Override
    public Boolean removeUserRole(UserRoleUpdateReq userRoleUpdateReq) {
        Long roleId = userRoleUpdateReq.getRoleId();
        List<Long> userIds = userRoleUpdateReq.getUserIds();
        if(Objects.isNull(roleId) || CollectionUtils.isEmpty(userIds))
            return false;
        userRoleDomainService.delUserRoles(roleId,userIds);
        return true;
    }
}
