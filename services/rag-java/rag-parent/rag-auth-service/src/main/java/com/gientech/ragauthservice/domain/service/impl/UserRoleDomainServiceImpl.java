package com.gientech.ragauthservice.domain.service.impl;

import com.gientech.ragauthservice.domain.entity.UserRole;
import com.gientech.ragauthservice.domain.repository.UserRoleRepository;
import com.gientech.ragauthservice.domain.service.UserRoleDomainService;
import com.gientech.ragauthservice.infrastructure.AuthProperties;
import com.gientech.ragcommon.auth.enums.RoleTypeEnums;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;

import java.util.List;
import java.util.Objects;
import java.util.stream.Collectors;

/**
 * <p>
 * 用户-角色关系表 服务实现类
 * </p>
 *
 * @author wudf
 * @since 2024-06-26
 */
@Service
public class UserRoleDomainServiceImpl implements UserRoleDomainService {

    @Autowired
    private UserRoleRepository userRoleRepository;

    @Autowired
    private AuthProperties authProperties;

    @Override
    public List<UserRole> queryByUserId(Long userId) {
        if(Objects.isNull(userId))
            return null;
        return userRoleRepository.queryByUserId(userId);
    }

    @Override
    public void addUserRoles(Long userId, List<Long> addRoleIds) {
        userRoleRepository.addUserRoles(userId,addRoleIds);
    }

    @Override
    public void addUserRoles(List<UserRole> userRoles) {
        userRoleRepository.addUserRoles(userRoles);
    }

    @Override
    public void delUserRoles(Long userId, List<Long> delRoleIds) {
        userRoleRepository.delUserRoles(userId,delRoleIds);
    }

    @Override
    public List<UserRole> queryByRoleId(Long roleId) {
        return userRoleRepository.queryByRoleId(roleId);
    }

    @Override
    public void deleteByuserIds(List<Long> userIds) {
        userRoleRepository.deleteByuserIds(userIds);
    }

    @Override
    public Integer getRoleType(long userId) {
        List<UserRole> userRoles = queryByUserId(userId);
        if(!CollectionUtils.isEmpty(userRoles)){
            List<Long> roleIds = userRoles.stream().map(UserRole::getRoleId).toList();
            return roleIds.contains(authProperties.getSuperRoleId()) ? RoleTypeEnums.SUPER_ADMIN.getCode() :
                    (roleIds.contains(authProperties.getAdminRoleId()) ? RoleTypeEnums.ADMIN.getCode() : null);
        }
        return null;
    }

    @Override
    public void deleteByRoleAndUser(Long roleId, List<Long> userIds) {
        userRoleRepository.deleteByRoleAndUser(roleId,userIds);
    }
}
