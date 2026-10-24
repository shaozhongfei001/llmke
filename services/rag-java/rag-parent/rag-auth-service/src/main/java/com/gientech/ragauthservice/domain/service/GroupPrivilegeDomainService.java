package com.gientech.ragauthservice.domain.service;

import com.gientech.ragauthservice.domain.entity.GroupPrivilege;
import com.gientech.ragcommon.auth.request.GroupPrivilegeReq;
import com.gientech.ragcommon.auth.request.UpdateGroupPermissionReq;

import java.util.List;

/**
 * <p>
 * 机构组-数据权限关联 服务类
 * </p>
 *
 * @author wudf
 * @since 2024-07-31
 */
public interface GroupPrivilegeDomainService {

    void delete(Integer bizType, Long targetId, List<Long> groupIds);

    void addBatch(GroupPrivilegeReq groupPrivilegeReq);

    void addBatchWithList(List<GroupPrivilege> groupPrivileges);

    Boolean deleteById(Long id);

    GroupPrivilege findbyCondtion(UpdateGroupPermissionReq groupPermissionReq);

    Boolean updateById(GroupPrivilege groupPrivilege);

    List<GroupPrivilege> findbyTypeAndId(Integer bizType, Long targetId);

    List<GroupPrivilege> findByTypeAndGroupIds(Integer bizType, List<Long> groupIdList, List<Long> targetId);

    List<GroupPrivilege> list(GroupPrivilege groupPrivilege);

    Boolean updatePermissionBatch(List<GroupPrivilege> groupPrivileges, Integer permission, Long elementId);
}
