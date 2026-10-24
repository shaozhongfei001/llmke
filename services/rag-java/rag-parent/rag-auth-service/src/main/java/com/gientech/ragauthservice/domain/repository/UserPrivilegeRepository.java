package com.gientech.ragauthservice.domain.repository;

import com.gientech.ragauthservice.domain.entity.UserPrivilege;
import com.gientech.ragcommon.auth.dto.PrivilegeDTO;
import com.gientech.ragcommon.auth.enums.PrivilegeTypeEnums;
import com.gientech.ragcommon.auth.request.UpdateUserPermissionReq;
import com.gientech.ragcommon.auth.request.UserPrivilegeReq;
import java.util.List;
import java.util.Map;

public interface UserPrivilegeRepository {

    void delete(Integer bizType, Long targetId, List<Long> userIds);

    void deleteByUserId(Integer bizType, List<Long> userIds);

    void addBatch(UserPrivilegeReq userPrivilegeReq);

    void addBatchWithList(List<UserPrivilege> userPrivileges);

    int updatePermissionBatch(List<Long> ids, Integer permission, Long elementId);

    List<PrivilegeDTO> getPermission(Long userId,Integer bizType,Long targetId);

    Boolean deleteById(Long id);

    UserPrivilege findbyCondtion(UpdateUserPermissionReq userPermissionReq);

    Boolean updateById(UserPrivilege userPrivilege);

    Boolean updateByMap(UserPrivilege userPrivilege, Map<String,Object> params);

    List<UserPrivilege> findbyTypeAndId(Integer bizType, Long targetId);

    List<UserPrivilege> list(UserPrivilege queryParam);

    List<Integer> getTransferType(Long userId, String userName);
}
