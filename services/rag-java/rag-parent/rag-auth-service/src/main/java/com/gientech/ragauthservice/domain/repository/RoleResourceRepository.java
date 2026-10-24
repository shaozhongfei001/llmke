package com.gientech.ragauthservice.domain.repository;

import com.gientech.ragauthservice.domain.entity.RoleResource;

import java.util.List;

public interface RoleResourceRepository {
    Boolean addRoleResource(Long roleId, List<Long> resourceIds);

    Boolean delRoleResource(Long roleId, List<Long> delResourceIds);

    List<RoleResource> listByRoleId(Long roleId);
}
