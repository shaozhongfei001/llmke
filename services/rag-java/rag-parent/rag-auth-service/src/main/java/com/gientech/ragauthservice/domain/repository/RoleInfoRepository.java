package com.gientech.ragauthservice.domain.repository;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragauthservice.domain.entity.RoleInfo;

import java.util.List;

public interface RoleInfoRepository {
    RoleInfo queryByName(String roleName);

    Boolean addRole(RoleInfo roleInfo);

    boolean updateRole(RoleInfo roleInfo);

    Page<RoleInfo> list(String idOrName, Integer status, Long pageNo, Long pageSize);

    List<RoleInfo> queryByIds(List<Long> roleIds);

    RoleInfo queryById(Long roleId,String roleName);

    RoleInfo queryById(Long roleId);

    List<RoleInfo> listAll();
}
