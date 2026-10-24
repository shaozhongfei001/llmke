package com.gientech.ragauthservice.domain.service.impl;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragauthservice.domain.entity.RoleInfo;
import com.gientech.ragauthservice.domain.repository.RoleInfoRepository;
import com.gientech.ragauthservice.domain.service.RoleInfoDomainService;
import com.gientech.ragcommon.auth.enums.IsDtlEnums;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

/**
 * <p>
 * 角色表 服务实现类
 * </p>
 *
 * @author wudf
 * @since 2024-06-26
 */
@Service
public class RoleInfoDomainServiceImpl implements RoleInfoDomainService {

    @Autowired
    private RoleInfoRepository roleInfoRepository;

    @Override
    public RoleInfo queryByName(String roleName) {
        return roleInfoRepository.queryByName(roleName);
    }

    @Override
    public Boolean addRole(RoleInfo roleInfo) {
        return roleInfoRepository.addRole(roleInfo);
    }

    @Override
    public boolean updateRole(RoleInfo roleInfo) {
        return roleInfoRepository.updateRole(roleInfo);
    }

    @Override
    public Boolean deleteRole(Long roleId) {
        RoleInfo roleInfo = new RoleInfo();
        roleInfo.setId(roleId);
        roleInfo.setIsDtl(IsDtlEnums.YES.getCode());
        return roleInfoRepository.updateRole(roleInfo);
    }

    @Override
    public Page<RoleInfo> list(String idOrName, Integer status, Long pageNo, Long pageSize) {
        return roleInfoRepository.list(idOrName,status,pageNo,pageSize);
    }

    @Override
    public List<RoleInfo> queryByIds(List<Long> roleIds) {
        return roleInfoRepository.queryByIds(roleIds);
    }

    @Override
    public RoleInfo queryById(Long roleId,String roleName) {
        return roleInfoRepository.queryById(roleId,roleName);
    }

    @Override
    public RoleInfo queryById(Long roleId) {
        return roleInfoRepository.queryById(roleId);
    }

    @Override
    public RoleInfo getRoleInfo(Long roleId) {
        return roleInfoRepository.queryById(roleId);
    }

    @Override
    public List<RoleInfo> listAll(){
        return roleInfoRepository.listAll();
    }
}
