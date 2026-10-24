package com.gientech.tools.database.domain.convertor;

import com.gientech.tools.database.domain.entity.TLDatabase;
import com.gientech.tools.database.domain.model.TLDatabaseDO;
import org.mapstruct.Mapper;
import org.mapstruct.factory.Mappers;

import java.util.List;

/**
 * 数据库配置;
 * @Author ： xiaomin.zuo@gientech.com
 * @date : 2025-7-11
 */
@Mapper
public interface TLDatabaseConvertor {
    TLDatabaseConvertor INSTANCE = Mappers.getMapper(TLDatabaseConvertor.class);

    List<TLDatabase> tlDatabaseDOList2TLDatabaseList(List<TLDatabaseDO> tlDatabaseDOS);

    TLDatabase tlDatabaseDO2TLDatabase(TLDatabaseDO tlDatabaseDO);
}
