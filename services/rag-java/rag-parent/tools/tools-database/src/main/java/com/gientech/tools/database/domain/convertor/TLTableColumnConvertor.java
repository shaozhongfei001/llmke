package com.gientech.tools.database.domain.convertor;

import com.gientech.tools.database.domain.entity.TLTableColumn;
import com.gientech.tools.database.domain.model.TLTableColumnDO;
import org.mapstruct.Mapper;
import org.mapstruct.factory.Mappers;

import java.util.List;

/**
 * 数据表-字段信息;
 * @Author ： xiaomin.zuo@gientech.com
 * @date : 2025-8-8
 */
@Mapper
public interface TLTableColumnConvertor {
    TLTableColumnConvertor INSTANCE = Mappers.getMapper(TLTableColumnConvertor.class);

    List<TLTableColumn> tlTableColumnDOList2TLTableColumnList(List<TLTableColumnDO> tlTableColumnDOS);

    TLTableColumn tlTableColumnDO2TLTableColumn(TLTableColumnDO tlTableColumnDO);

    List<TLTableColumnDO> tlTableColumnList2TLTableColumnDOList(List<TLTableColumn> tlTableColumns);
}
