package com.gientech.ragauthservice.application.service;

import com.gientech.ragcommon.auth.dto.*;
import com.gientech.ragcommon.auth.enums.PrivilegeTypeEnums;
import com.gientech.ragcommon.auth.request.*;
import com.gientech.ragcommon.index.dto.Collaborator;

import java.util.List;
import java.util.Map;

public interface PrivilegeAppService {

    Boolean setUserPrivilege(UserPrivilegeReq userPermissionReq);

    Boolean setUserPrivilegeWithList(List<UserPrivilegeBatchReq> userPrivilegeBatchReqs);

    Boolean setGroupPrivilege(GroupPrivilegeReq groupPermissionReq);

    Boolean setGroupPrivilegeWithList(List<GroupPrivilegeBatchReq> groupPrivilegeBatchReqs);

    Map<Long, PrivilegeDTO> getPermission(Integer bizType, String userName);

    List<GroupPrivilegeDTO> getGroups(Integer bizType, Long targetId);

    List<UserPrivilegeDTO> getUsers(Integer bizType, Long targetId);

    Boolean updateGroupPermission(UpdateGroupPermissionReq groupPermissionReq);

    Boolean updateUserPermission(UpdateUserPermissionReq userPermissionReq);

    Boolean deleteGroupPermission(Long id);

    Boolean deleteUserPermission(Long id);

    Boolean isPermission(Integer bizType, Long targetId);

    List<Collaborator> getUserListGroupByPermission(Long kbId, Integer bizType, Long targetId);

    Boolean setDeptPrivilege(DeptPrivilegeReq deptPermissionReq);

    Boolean setDeptPrivilegeWithList(List<DeptPrivilegeBatchReq> deptPrivilegeBatchReqs);

    Boolean updateCurrentPermissionByBizType(UpdatePermissionReq req);

    List<DeptPrivilegeDTO> getDeptList(Integer bizType, Long targetId);

    Boolean updateDeptPermission(UpdateDeptPermissionReq deptPermissionReq);

    Boolean deleteDeptPermission(Long id);

    /**
     * 获取所有人的访问权限
     * @param bizType
     * @param targetId
     * @return
     */
    PublicAccessPrivilegeDTO getPublicAccess(Integer bizType, Long targetId);

    /**
     * 获取指定用户或当前用户的指定类型的全部数据权限,若存在重复,则取权限较高的
     * @param bizType
     * @param userName
     * @return
     */
    List<PrivilegeDTO> getAllPermission(Integer bizType, String userName, Long[] targetIds);

    List<PrivilegeDTO> getPermissionByTargetId(Integer bizType, Long[] targetIds);
    /**
     * 获取数据权限下的所有人、用户、部门、用户组
     * @param bizType
     * @param targetId
     * @return
     */
    List<AllPrivilegeDTO> getAllList(Integer bizType, Long targetId);

    Boolean transferProperty(List<TransferPropertyReq> reqs) throws Exception;

    List<PrivilegeTypeEnums> getTransferType(Long userId);
}
