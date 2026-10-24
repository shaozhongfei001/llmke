package com.gientech.ragcommon.auth.convertor;

import com.gientech.ragcommon.index.enmus.PermissionEnums;
import org.mapstruct.Mapper;
import org.mapstruct.factory.Mappers;

@Mapper
public interface PermissionEnumConvertor {
    PermissionEnumConvertor INSTANCE = Mappers.getMapper(PermissionEnumConvertor.class);

    default Integer toCode(PermissionEnums permissionEnum) {
        return permissionEnum.getCode();
    }

    default PermissionEnums fromCode(Integer code) {
        return PermissionEnums.of(code);
    }
}
