package com.gientech.ragcommon.auth.convertor;

import com.gientech.ragcommon.auth.enums.FrameElementTypeEnums;
import org.mapstruct.Mapper;
import org.mapstruct.factory.Mappers;

@Mapper
public interface FrameElementTypeEnumConvertor {
    FrameElementTypeEnumConvertor INSTANCE = Mappers.getMapper(FrameElementTypeEnumConvertor.class);

    default Integer toCode(FrameElementTypeEnums typeEnum){
        return typeEnum.getType();
    }

    default FrameElementTypeEnums fromCode(Integer code){
        return FrameElementTypeEnums.of(code);
    }

}
