package com.gientech.ragauthservice.infrastructure.convertor;

import com.gientech.ragauthservice.domain.entity.UserPrivilege;
import com.gientech.ragauthservice.domain.model.UserPrivilegeDO;
import com.gientech.ragcommon.auth.dto.UserPrivilegeDTO;
import com.gientech.ragcommon.auth.request.UserPrivilegeBatchReq;
import org.mapstruct.Mapper;
import org.mapstruct.Mapping;
import org.mapstruct.factory.Mappers;

import java.util.ArrayList;
import java.util.List;

@Mapper
public interface UserPrivilegeConvertor {
    UserPrivilegeConvertor INSTANCE = Mappers.getMapper(UserPrivilegeConvertor.class);

    default UserPrivilegeDO userPrivilege2DO(UserPrivilege userPrivilege) {
        if ( userPrivilege == null ) {
            return null;
        }

        UserPrivilegeDO.UserPrivilegeDOBuilder userPrivilegeDO = UserPrivilegeDO.builder();

        userPrivilegeDO.id( userPrivilege.getId() );
        userPrivilegeDO.targetId( userPrivilege.getTargetId() );
        userPrivilegeDO.userId( userPrivilege.getUserId() );
        userPrivilegeDO.bizType( userPrivilege.getBizType() );
        userPrivilegeDO.permission( userPrivilege.getPermission() );
        userPrivilegeDO.gmtCreate( userPrivilege.getGmtCreate() );
        userPrivilegeDO.gmtModified( userPrivilege.getGmtModified() );
        userPrivilegeDO.createBy( userPrivilege.getCreateBy() );
        userPrivilegeDO.updateBy( userPrivilege.getUpdateBy() );

        return userPrivilegeDO.build();
    }

    UserPrivilege userPrivilegeDTO2UserPrivilege(UserPrivilegeDTO userPrivilegeDTO);

    default UserPrivilege req2UserPrivilege(UserPrivilegeBatchReq userPrivilegeBatchReq){
        if ( userPrivilegeBatchReq == null ) {
            return null;
        }

        UserPrivilege.UserPrivilegeBuilder userPrivilege = UserPrivilege.builder();

        userPrivilege.targetId( userPrivilegeBatchReq.getTargetId() );
        userPrivilege.userId( userPrivilegeBatchReq.getUserId() );
        userPrivilege.bizType( userPrivilegeBatchReq.getBizType() );
        userPrivilege.permission( userPrivilegeBatchReq.getPermission() );

        return userPrivilege.build();
    }

    List<UserPrivilegeDO> userPrivilege2DOS(List<UserPrivilege> userPrivileges);

    default List<UserPrivilege> req2UserPrivileges(List<UserPrivilegeBatchReq> userPrivilegeBatchReqs){
        if ( userPrivilegeBatchReqs == null ) {
            return null;
        }

        List<UserPrivilege> list = new ArrayList<UserPrivilege>( userPrivilegeBatchReqs.size() );
        for ( UserPrivilegeBatchReq userPrivilegeBatchReq : userPrivilegeBatchReqs ) {
            list.add( req2UserPrivilege( userPrivilegeBatchReq ) );
        }

        return list;
    }
}
