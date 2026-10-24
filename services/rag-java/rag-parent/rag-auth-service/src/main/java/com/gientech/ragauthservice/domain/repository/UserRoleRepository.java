package com.gientech.ragauthservice.domain.repository;



import com.gientech.ragauthservice.domain.entity.UserRole;

import java.io.Serializable;
import java.util.List;

public interface UserRoleRepository {


    List<UserRole> queryByUserId(Long userId);

    void addUserRoles(Long userId, List<Long> addRoleIds);

    void addUserRoles(List<UserRole> userRoles);

    void delUserRoles(Long userId, List<Long> delRoleIds);

    List<UserRole> queryByRoleId(Long roleId);

    void deleteByuserIds(List<Long> userIds);

    void deleteByRoleAndUser(Long roleId, List<Long> userIds);
}
