package com.gientech.ragauthservice.infrastructure.convertor;

import com.gientech.ragauthservice.domain.entity.DeptPrivilege;
import com.gientech.ragauthservice.domain.model.DeptPrivilegeDO;
import com.gientech.ragcommon.auth.request.DeptPrivilegeBatchReq;
import org.mapstruct.Mapper;
import org.mapstruct.factory.Mappers;

import java.util.ArrayList;
import java.util.List;

@Mapper
public interface DeptPrivilegeConvertor {
    DeptPrivilegeConvertor INSTANCE = Mappers.getMapper(DeptPrivilegeConvertor.class);

    default DeptPrivilegeDO deptPrivilege2DO(DeptPrivilege deptPrivilege) {
        if (deptPrivilege == null) {
            return null;
        }

        DeptPrivilegeDO.DeptPrivilegeDOBuilder deptPrivilegeDO = DeptPrivilegeDO.builder();

        deptPrivilegeDO.id(deptPrivilege.getId());
        deptPrivilegeDO.targetId(deptPrivilege.getTargetId());
        deptPrivilegeDO.deptId(deptPrivilege.getDeptId());
        deptPrivilegeDO.bizType(deptPrivilege.getBizType());
        deptPrivilegeDO.permission(deptPrivilege.getPermission());
        deptPrivilegeDO.gmtCreate(deptPrivilege.getGmtCreate());
        deptPrivilegeDO.gmtModified(deptPrivilege.getGmtModified());
        deptPrivilegeDO.createBy(deptPrivilege.getCreateBy());
        deptPrivilegeDO.updateBy(deptPrivilege.getUpdateBy());

        return deptPrivilegeDO.build();
    }

    default DeptPrivilege req2DeptPrivilege(DeptPrivilegeBatchReq deptPrivilegeBatchReq) {
        if (deptPrivilegeBatchReq == null) {
            return null;
        }

        DeptPrivilege deptPrivilege = new DeptPrivilege();

        deptPrivilege.setTargetId(deptPrivilegeBatchReq.getTargetId());
        deptPrivilege.setDeptId(deptPrivilegeBatchReq.getDeptId());
        deptPrivilege.setBizType(deptPrivilegeBatchReq.getBizType());
        deptPrivilege.setPermission(deptPrivilegeBatchReq.getPermission());

        return deptPrivilege;
    }

    List<DeptPrivilegeDO> deptPrivileges2DOS(List<DeptPrivilege> deptPrivileges);

    default List<DeptPrivilege> reqs2DeptPrivileges(List<DeptPrivilegeBatchReq> deptPrivilegeBatchReqs) {
        if (deptPrivilegeBatchReqs == null) {
            return null;
        }

        List<DeptPrivilege> list = new ArrayList<DeptPrivilege>(deptPrivilegeBatchReqs.size());
        for (DeptPrivilegeBatchReq deptPrivilegeBatchReq : deptPrivilegeBatchReqs) {
            list.add(req2DeptPrivilege(deptPrivilegeBatchReq));
        }

        return list;
    }
}
