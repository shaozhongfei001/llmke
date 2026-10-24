package com.gientech.ragqaservice.domain.conventer;

import com.gientech.ragcommon.qa.enmus.SysTypeEnums;
import org.mapstruct.Mapper;
import org.mapstruct.factory.Mappers;

/**
 * @Description:
 * @Author: chenjuan
 * @Date: 2024/9/27 15:02
 */
@Mapper
public interface SysTypeEnumConvertor {

    SysTypeEnumConvertor INSTANCE = Mappers.getMapper(SysTypeEnumConvertor.class);

    default Integer toInteger(SysTypeEnums sysTypeEnums) {
        return sysTypeEnums.getCode();
    }
}
