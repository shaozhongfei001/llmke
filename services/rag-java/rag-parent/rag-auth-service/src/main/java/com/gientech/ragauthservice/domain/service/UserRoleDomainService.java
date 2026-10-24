package com.gientech.ragauthservice.domain.service;

import com.gientech.ragauthservice.domain.entity.UserRole;

import java.util.List;

/**
 * <p>
 * 用户-角色关系表 服务类
 * </p>
 *
 * @author wudf
 * @since 2024-06-26
 */
public interface UserRoleDomainService  {

    List<UserRole> queryByUserId(Long userId);

    void addUserRoles(Long userId, List<Long> addRoleIds);

    void addUserRoles(List<UserRole> userRoles);

    void delUserRoles(Long userId, List<Long> delRoleIds);

    List<UserRole> queryByRoleId(Long roleId);

    void deleteByuserIds(List<Long> userIds);

    void deleteByRoleAndUser(Long roleId,List<Long> userIds);

    Integer getRoleType(long parseLong);
}
