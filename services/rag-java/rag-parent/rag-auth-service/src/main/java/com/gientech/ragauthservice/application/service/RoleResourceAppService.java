package com.gientech.ragauthservice.application.service;

import com.gientech.ragauthservice.interfaces.dto.RoleResourceDTO;

import java.util.List;

public interface RoleResourceAppService {
    List<RoleResourceDTO> listByRoleId(Long roleId);

    Boolean addRoleResource(Long roleId, List<Long> resourceIds);

    Boolean delRoleResource(Long roleId, List<Long> delResourceIds);
}
