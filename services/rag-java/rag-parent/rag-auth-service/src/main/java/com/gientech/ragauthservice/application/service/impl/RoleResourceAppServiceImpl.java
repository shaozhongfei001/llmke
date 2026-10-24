package com.gientech.ragauthservice.application.service.impl;

import cn.hutool.core.bean.BeanUtil;
import com.gientech.ragauthservice.application.service.RoleResourceAppService;
import com.gientech.ragauthservice.domain.service.RoleResourceDomainService;
import com.gientech.ragauthservice.interfaces.dto.RoleResourceDTO;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class RoleResourceAppServiceImpl implements RoleResourceAppService {
    private final RoleResourceDomainService roleResourceDomainService;

    public RoleResourceAppServiceImpl(RoleResourceDomainService roleResourceDomainService) {
        this.roleResourceDomainService = roleResourceDomainService;
    }

    @Override
    public List<RoleResourceDTO> listByRoleId(Long roleId) {
        return BeanUtil.copyToList(roleResourceDomainService.listByRoleId(roleId), RoleResourceDTO.class);
    }

    @Override
    public Boolean addRoleResource(Long roleId, List<Long> resourceIds) {
        return roleResourceDomainService.addRoleResource(roleId, resourceIds);
    }

    @Override
    public Boolean delRoleResource(Long roleId, List<Long> delResourceIds) {
        return roleResourceDomainService.delRoleResource(roleId, delResourceIds);
    }
}
