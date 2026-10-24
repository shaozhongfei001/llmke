package com.gientech.ragauthservice.domain.service.impl;

import com.gientech.ragauthservice.domain.entity.UserPrivilege;
import com.gientech.ragauthservice.domain.repository.UserPrivilegeRepository;
import com.gientech.ragauthservice.domain.service.UserPrivilegeDomainService;
import com.gientech.ragcommon.auth.dto.PrivilegeDTO;
import com.gientech.ragcommon.auth.enums.PrivilegeTypeEnums;
import com.gientech.ragcommon.auth.request.UpdateUserPermissionReq;
import com.gientech.ragcommon.auth.request.UserPrivilegeReq;
import com.google.common.collect.Maps;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;

import java.util.List;
import java.util.Map;
import java.util.Objects;

/**
 * <p>
 * 用户-数据权限关联 服务实现类
 * </p>
 *
 * @author wudf
 * @since 2024-07-31
 */
@Service
public class UserPrivilegeDomainServiceImpl implements UserPrivilegeDomainService {

    @Autowired
    private UserPrivilegeRepository userPrivilegeRepository;

    @Override
    public void delete(Integer bizType, Long targetId, List<Long> userIds) {
        userPrivilegeRepository.delete(bizType, targetId, userIds);
    }

    @Override
    public void deleteByUserId(Integer bizType, List<Long> userIds) {
        userPrivilegeRepository.deleteByUserId(bizType, userIds);
    }

    @Override
    public void addBatch(UserPrivilegeReq userPrivilegeReq) {
        userPrivilegeRepository.addBatch(userPrivilegeReq);
    }


    @Override
    public void addBatchWithList(List<UserPrivilege> userPrivileges) {
        userPrivilegeRepository.addBatchWithList(userPrivileges);
    }

    @Override
    public Boolean updatePermissionBatch(List<UserPrivilege> userPrivileges, Integer permission, Long elementId) {
        List<Long> ids = userPrivileges.stream().map(UserPrivilege::getId).toList();
        return userPrivilegeRepository.updatePermissionBatch(ids, permission, elementId) > 0;
    }

    @Override
    public Map<Long, PrivilegeDTO> getPermission(Long userId, Integer bizType, Long targetId) {
        List<PrivilegeDTO> permissions = userPrivilegeRepository.getPermission(userId, bizType, targetId);
        Map<Long, PrivilegeDTO> permissionMap = Maps.newHashMap();
        if (!CollectionUtils.isEmpty(permissions)) {
            permissions.forEach(permission -> {
                PrivilegeDTO privilegeDTO = permissionMap.get(permission.getTargetId());
                if (Objects.isNull(privilegeDTO) || (permission.getPermission() > privilegeDTO.getPermission()))
                    permissionMap.put(permission.getTargetId(), permission);
            });
        }
        return permissionMap;
    }

    @Override
    public Boolean deleteById(Long id) {
        return userPrivilegeRepository.deleteById(id);
    }

    @Override
    public UserPrivilege findbyCondtion(UpdateUserPermissionReq userPermissionReq) {
        return userPrivilegeRepository.findbyCondtion(userPermissionReq);
    }

    @Override
    public Boolean updateById(UserPrivilege userPrivilege) {
        return userPrivilegeRepository.updateById(userPrivilege);
    }


    @Override
    public Boolean updateByMap(UserPrivilege userPrivilege, Map<String, Object> params) {
        return userPrivilegeRepository.updateByMap(userPrivilege, params);
    }

    @Override
    public List<UserPrivilege> findbyTypeAndId(Integer bizType, Long targetId) {
        return userPrivilegeRepository.findbyTypeAndId(bizType, targetId);
    }

    @Override
    public List<UserPrivilege> list(UserPrivilege queryParam) {
        return userPrivilegeRepository.list(queryParam);
    }

    @Override
    public List<PrivilegeTypeEnums> getTransferType(Long userId, String userName) {
        List<Integer> transferTypes = userPrivilegeRepository.getTransferType(userId, userName);
        return PrivilegeTypeEnums.transferTypeList(transferTypes);
    }
}
