package com.gientech.ragauthservice.domain.service.impl;

import com.gientech.ragauthservice.domain.entity.DeptPrivilege;
import com.gientech.ragauthservice.domain.repository.DeptPrivilegeRepository;
import com.gientech.ragauthservice.domain.service.DeptPrivilegeDomainService;
import com.gientech.ragcommon.auth.request.DeptPrivilegeReq;
import com.gientech.ragcommon.auth.request.UpdateDeptPermissionReq;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

/**
 * @Desc 部门-数据权限关联 服务实现类
 * @Author ZhenPanHong
 * @Date 2025/3/11 15:22
 */
@Service
public class DeptPrivilegeDomainServiceImpl implements DeptPrivilegeDomainService {

    @Autowired
    private DeptPrivilegeRepository deptPrivilegeRepository;

    @Override
    public void delete(Integer bizType, Long targetId, List<Long> groupIds) {
        deptPrivilegeRepository.delete(bizType, targetId, groupIds);
    }

    @Override
    public void addBatch(DeptPrivilegeReq deptPrivilegeReq) {
        deptPrivilegeRepository.addBatch(deptPrivilegeReq);
    }

    @Override
    public Boolean updatePermissionBatch(List<DeptPrivilege> deptPrivileges, Integer permission, Long elementId) {
        List<Long> ids = deptPrivileges.stream().map(DeptPrivilege::getId).toList();
        return deptPrivilegeRepository.updatePermissionBatch(ids, permission, elementId) > 0;
    }

    @Override
    public void addBatchWithList(List<DeptPrivilege> deptPrivileges) {
        deptPrivilegeRepository.addBatchWithList(deptPrivileges);
    }

    @Override
    public Boolean deleteById(Long id) {
        return deptPrivilegeRepository.deleteById(id);
    }

    @Override
    public DeptPrivilege findByCondition(UpdateDeptPermissionReq updateDeptPermissionReq) {
        return deptPrivilegeRepository.findByCondition(updateDeptPermissionReq);
    }

    @Override
    public Boolean updateById(DeptPrivilege deptPrivilege) {
        return deptPrivilegeRepository.updateById(deptPrivilege);
    }

    @Override
    public List<DeptPrivilege> findByTypeAndId(Integer bizType, Long targetId) {
        return deptPrivilegeRepository.findByTypeAndId(bizType, targetId);
    }

    @Override
    public List<DeptPrivilege> list(DeptPrivilege queryParam) {
        return deptPrivilegeRepository.list(queryParam);
    }
}
