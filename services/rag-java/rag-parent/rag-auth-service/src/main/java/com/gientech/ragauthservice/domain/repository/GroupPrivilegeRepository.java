package com.gientech.ragauthservice.domain.repository;

import com.gientech.ragauthservice.domain.entity.GroupPrivilege;
import com.gientech.ragcommon.auth.request.GroupPrivilegeReq;
import com.gientech.ragcommon.auth.request.UpdateGroupPermissionReq;

import java.util.List;

public interface GroupPrivilegeRepository {

    void delete(Integer bizType, Long targetId, List<Long> groupIds);

    void addBatch(GroupPrivilegeReq groupPrivilegeReq);

    int updatePermissionBatch(List<Long> ids, Integer permission, Long elementId);

    void addBatchWithList(List<GroupPrivilege> groupPrivileges);

    Boolean deleteById(Long id);

    GroupPrivilege findbyCondtion(UpdateGroupPermissionReq groupPermissionReq);

    Boolean updateById(GroupPrivilege groupPrivilege);

    List<GroupPrivilege> findbyTypeAndId(Integer bizType, Long targetId);

    List<GroupPrivilege> findByTypeAndGroupIds(Integer bizType, List<Long> groupIdList, List<Long> targetIds);

    List<GroupPrivilege> list(GroupPrivilege groupPrivilege);
}
