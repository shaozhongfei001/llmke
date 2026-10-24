package com.gientech.ragauthservice.infrastructure.convertor;

import com.gientech.ragauthservice.domain.entity.GroupPrivilege;
import com.gientech.ragauthservice.domain.model.GroupPrivilegeDO;
import com.gientech.ragcommon.auth.dto.GroupPrivilegeDTO;
import com.gientech.ragcommon.auth.request.GroupPrivilegeBatchReq;
import org.mapstruct.Mapper;
import org.mapstruct.Mapping;
import org.mapstruct.factory.Mappers;

import java.util.ArrayList;
import java.util.List;

/**
 * @author chenjuan
 * @date 2025/3/24 17:21
 */
@Mapper
public interface GroupPrivilegeConvertor {
    GroupPrivilegeConvertor INSTANCE = Mappers.getMapper(GroupPrivilegeConvertor.class);

    default GroupPrivilegeDO groupPrivilege2DO(GroupPrivilege groupPrivilege) {
        if ( groupPrivilege == null ) {
            return null;
        }

        GroupPrivilegeDO.GroupPrivilegeDOBuilder groupPrivilegeDO = GroupPrivilegeDO.builder();

        groupPrivilegeDO.id( groupPrivilege.getId() );
        groupPrivilegeDO.targetId( groupPrivilege.getTargetId() );
        groupPrivilegeDO.groupId( groupPrivilege.getGroupId() );
        groupPrivilegeDO.bizType( groupPrivilege.getBizType() );
        groupPrivilegeDO.permission( groupPrivilege.getPermission() );
        groupPrivilegeDO.gmtCreate( groupPrivilege.getGmtCreate() );
        groupPrivilegeDO.gmtModified( groupPrivilege.getGmtModified() );
        groupPrivilegeDO.createBy( groupPrivilege.getCreateBy() );
        groupPrivilegeDO.updateBy( groupPrivilege.getUpdateBy() );

        return groupPrivilegeDO.build();
    }

    List<GroupPrivilegeDO> groupPrivileges2DOS(List<GroupPrivilege> groupPrivileges);

    default GroupPrivilege req2GroupPrivilege(GroupPrivilegeBatchReq groupPrivilegeBatchReq){
        if ( groupPrivilegeBatchReq == null ) {
            return null;
        }

        GroupPrivilege groupPrivilege = new GroupPrivilege();

        groupPrivilege.setTargetId( groupPrivilegeBatchReq.getTargetId() );
        groupPrivilege.setGroupId( groupPrivilegeBatchReq.getGroupId() );
        groupPrivilege.setBizType( groupPrivilegeBatchReq.getBizType() );
        groupPrivilege.setPermission( groupPrivilegeBatchReq.getPermission() );

        return groupPrivilege;
    }

    GroupPrivilege dto2GroupPrivilege(GroupPrivilegeDTO groupPrivilegeDTO);

    default List<GroupPrivilege> reqs2GroupPrivileges(List<GroupPrivilegeBatchReq> groupPrivilegeBatchReqs){
        if ( groupPrivilegeBatchReqs == null ) {
            return null;
        }

        List<GroupPrivilege> list = new ArrayList<GroupPrivilege>( groupPrivilegeBatchReqs.size() );
        for ( GroupPrivilegeBatchReq groupPrivilegeBatchReq : groupPrivilegeBatchReqs ) {
            list.add( req2GroupPrivilege( groupPrivilegeBatchReq ) );
        }

        return list;
    }
}
