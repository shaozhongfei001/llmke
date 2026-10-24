package com.gientech.tools.database.domain.convertor;

import com.gientech.tools.database.domain.entity.TLTable;
import com.gientech.tools.database.domain.model.TLTableDO;
import org.mapstruct.Mapper;
import org.mapstruct.factory.Mappers;

import java.util.List;

/**
 * 数据库配置;
 * @Author ： xiaomin.zuo@gientech.com
 * @date : 2025-7-11
 */
@Mapper
public interface TLTableConvertor {
    TLTableConvertor INSTANCE = Mappers.getMapper(TLTableConvertor.class);

    List<TLTable> tlTableDOList2TLTableList(List<TLTableDO> tlTableDOS);

    TLTable tlTableDO2TLTable(TLTableDO tlTableDO);
}
