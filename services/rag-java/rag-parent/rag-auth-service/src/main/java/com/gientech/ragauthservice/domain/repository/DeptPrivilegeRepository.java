package com.gientech.ragauthservice.domain.repository;

import com.gientech.ragauthservice.domain.entity.DeptPrivilege;
import com.gientech.ragcommon.auth.request.DeptPrivilegeReq;
import com.gientech.ragcommon.auth.request.UpdateDeptPermissionReq;

import java.util.List;

/**
 * @Desc 部门-数据权限关联 资源类
 * @Author ZhenPanHong
 * @Date 2025/3/11 15:13
 */
public interface DeptPrivilegeRepository {
    void delete(Integer bizType, Long targetId, List<Long> deptIds);

    void addBatch(DeptPrivilegeReq deptPrivilegeReq);

    int updatePermissionBatch(List<Long> ids, Integer permission, Long elementId);

    void addBatchWithList(List<DeptPrivilege> deptPrivileges);

    Boolean deleteById(Long id);

    DeptPrivilege findByCondition(UpdateDeptPermissionReq updateDeptPermissionReq);

    Boolean updateById(DeptPrivilege deptPrivilege);

    List<DeptPrivilege> findByTypeAndId(Integer bizType, Long targetId);

    List<DeptPrivilege> list(DeptPrivilege queryParam);
}
