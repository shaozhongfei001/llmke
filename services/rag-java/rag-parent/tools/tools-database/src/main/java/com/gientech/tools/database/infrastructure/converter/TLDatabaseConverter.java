package com.gientech.tools.database.infrastructure.converter;

import com.gientech.tools.database.domain.entity.TLDatabase;
import com.gientech.ragcommon.index.dto.tools.TLDatabaseDTO;
import org.mapstruct.Mapper;
import org.mapstruct.factory.Mappers;

/**
 * @author: shirleychen
 * @date 2025/9/11 10:00
 * @description
 */
@Mapper
public interface TLDatabaseConverter {
    TLDatabaseConverter INSTANCE = Mappers.getMapper(TLDatabaseConverter.class);

    TLDatabaseDTO convert(TLDatabase dto);
}
