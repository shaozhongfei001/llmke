package com.gientech.ragcommon.auth.convertor;

import com.gientech.ragcommon.auth.dto.AllPrivilegeDTO;
import com.gientech.ragcommon.index.dto.Collaborator;
import org.mapstruct.Mapper;
import org.mapstruct.factory.Mappers;

import java.util.List;

/**
 * @author chenjuan
 * @date 2025/3/24 14:32
 */
@Mapper(uses = {PermissionEnumConvertor.class})
public interface CollaboratorConvertor {
    CollaboratorConvertor INSTANCE = Mappers.getMapper(CollaboratorConvertor.class);

    List<Collaborator> allPrivilege2Collaborators(List<AllPrivilegeDTO> allPrivileges);

}
