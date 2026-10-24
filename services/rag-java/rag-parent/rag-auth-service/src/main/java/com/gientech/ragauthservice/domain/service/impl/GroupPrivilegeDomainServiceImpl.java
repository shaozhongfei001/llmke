package com.gientech.ragauthservice.domain.service.impl;

import com.gientech.ragauthservice.domain.entity.GroupPrivilege;
import com.gientech.ragauthservice.domain.repository.GroupPrivilegeRepository;
import com.gientech.ragauthservice.domain.service.GroupPrivilegeDomainService;
import com.gientech.ragcommon.auth.request.GroupPrivilegeReq;
import com.gientech.ragcommon.auth.request.UpdateGroupPermissionReq;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

/**
 * <p>
 * 机构组-数据权限关联 服务实现类
 * </p>
 *
 * @author wudf
 * @since 2024-07-31
 */
@Service
public class GroupPrivilegeDomainServiceImpl implements GroupPrivilegeDomainService {

    @Autowired
    private GroupPrivilegeRepository groupPrivilegeRepository;

    @Override
    public void delete(Integer bizType, Long targetId, List<Long> groupIds) {
        groupPrivilegeRepository.delete(bizType, targetId, groupIds);
    }

    @Override
    public void addBatch(GroupPrivilegeReq groupPrivilegeReq) {
        groupPrivilegeRepository.addBatch(groupPrivilegeReq);
    }

    @Override
    public void addBatchWithList(List<GroupPrivilege> groupPrivileges) {
        groupPrivilegeRepository.addBatchWithList(groupPrivileges);
    }

    @Override
    public Boolean deleteById(Long id) {
        return groupPrivilegeRepository.deleteById(id);
    }

    @Override
    public GroupPrivilege findbyCondtion(UpdateGroupPermissionReq groupPermissionReq) {
        return groupPrivilegeRepository.findbyCondtion(groupPermissionReq);
    }

    @Override
    public Boolean updateById(GroupPrivilege groupPrivilege) {
        return groupPrivilegeRepository.updateById(groupPrivilege);
    }

    @Override
    public List<GroupPrivilege> findbyTypeAndId(Integer bizType, Long targetId) {
        return groupPrivilegeRepository.findbyTypeAndId(bizType, targetId);
    }

    @Override
    public List<GroupPrivilege> findByTypeAndGroupIds(Integer bizType, List<Long> groupIdList, List<Long> targetIds) {
        return groupPrivilegeRepository.findByTypeAndGroupIds(bizType, groupIdList, targetIds);
    }

    @Override
    public List<GroupPrivilege> list(GroupPrivilege groupPrivilege) {
        return groupPrivilegeRepository.list(groupPrivilege);
    }

    @Override
    public Boolean updatePermissionBatch(List<GroupPrivilege> groupPrivileges, Integer permission, Long elementId) {
        List<Long> ids = groupPrivileges.stream().map(GroupPrivilege::getId).toList();
        return groupPrivilegeRepository.updatePermissionBatch(ids, permission, elementId) > 0;
    }
}
