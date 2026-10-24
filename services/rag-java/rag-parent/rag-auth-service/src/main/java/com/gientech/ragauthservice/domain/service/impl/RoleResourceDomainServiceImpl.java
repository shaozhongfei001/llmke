package com.gientech.ragauthservice.domain.service.impl;

import com.gientech.ragauthservice.domain.entity.RoleResource;
import com.gientech.ragauthservice.domain.repository.RoleResourceRepository;
import com.gientech.ragauthservice.domain.service.RoleResourceDomainService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

/**
 * <p>
 * 角色-资源关系表 服务实现类
 * </p>
 *
 * @author wudf
 * @since 2024-06-27
 */
@Service
public class RoleResourceDomainServiceImpl implements RoleResourceDomainService {

    @Autowired
    private RoleResourceRepository roleResourceRepository;

    @Override
    public Boolean addRoleResource(Long roleId, List<Long> resourceIds) {
        return roleResourceRepository.addRoleResource(roleId,resourceIds);
    }

    @Override
    public Boolean delRoleResource(Long roleId, List<Long> delResourceIds) {
        return roleResourceRepository.delRoleResource(roleId,delResourceIds);
    }

    @Override
    public List<RoleResource> listByRoleId(Long roleId){
        return roleResourceRepository.listByRoleId(roleId);
    }

}
