package com.gientech.ragauthservice.domain.service;

import com.gientech.ragauthservice.domain.entity.DeptPrivilege;
import com.gientech.ragcommon.auth.request.DeptPrivilegeReq;
import com.gientech.ragcommon.auth.request.UpdateDeptPermissionReq;

import java.util.List;

/**
 * @Desc 部门-数据权限关联 服务类
 * @Author ZhenPanHong
 * @Date 2025/3/11 15:20
 */
public interface DeptPrivilegeDomainService {
    void delete(Integer bizType, Long targetId, List<Long> groupIds);

    void addBatch(DeptPrivilegeReq deptPrivilegeReq);

    Boolean updatePermissionBatch(List<DeptPrivilege> deptPrivileges, Integer permission, Long elementId);

    void addBatchWithList(List<DeptPrivilege> deptPrivileges);

    Boolean deleteById(Long id);

    DeptPrivilege findByCondition(UpdateDeptPermissionReq updateDeptPermissionReq);

    Boolean updateById(DeptPrivilege deptPrivilege);

    List<DeptPrivilege> findByTypeAndId(Integer bizType, Long targetId);

    List<DeptPrivilege> list(DeptPrivilege queryParam);
}
