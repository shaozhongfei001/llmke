package com.gientech.ragauthservice.domain.service;

import com.gientech.ragauthservice.domain.entity.UserPrivilege;
import com.gientech.ragcommon.auth.dto.PrivilegeDTO;
import com.gientech.ragcommon.auth.enums.PrivilegeTypeEnums;
import com.gientech.ragcommon.auth.request.UpdateUserPermissionReq;
import com.gientech.ragcommon.auth.request.UserPrivilegeReq;

import java.util.List;
import java.util.Map;

/**
 * <p>
 * 用户-数据权限关联 服务类
 * </p>
 *
 * @author wudf
 * @since 2024-07-31
 */
public interface UserPrivilegeDomainService {

    void delete(Integer bizType, Long targetId, List<Long> userIds);

    void deleteByUserId(Integer bizType, List<Long> userIds);

    void addBatch(UserPrivilegeReq userPrivilegeReq);

    void addBatchWithList(List<UserPrivilege> userPrivileges);

    Boolean updatePermissionBatch(List<UserPrivilege> deptPrivileges, Integer permission, Long elementId);

    Map<Long, PrivilegeDTO> getPermission(Long UserId, Integer bizType, Long targetId);

    Boolean deleteById(Long id);

    UserPrivilege findbyCondtion(UpdateUserPermissionReq userPermissionReq);

    Boolean updateById(UserPrivilege userPrivilege);

    Boolean updateByMap(UserPrivilege userPrivilege, Map<String, Object> params);

    List<UserPrivilege> findbyTypeAndId(Integer bizType, Long targetId);

    List<UserPrivilege> list(UserPrivilege queryParam);

    List<PrivilegeTypeEnums> getTransferType(Long userId, String userName);
}
