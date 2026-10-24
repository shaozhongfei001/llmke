package com.gientech.tools.database.domain.convertor;

import com.gientech.tools.database.domain.entity.TLTableFile;
import com.gientech.tools.database.domain.model.TLTableFileDO;
import org.mapstruct.Mapper;
import org.mapstruct.factory.Mappers;

import java.util.List;

/**
 * 数据表-上传文件表;
 * @Author ： xiaomin.zuo@gientech.com
 * @date : 2025-7-11
 */
@Mapper
public interface TLTableFileConvertor {
    TLTableFileConvertor INSTANCE = Mappers.getMapper(TLTableFileConvertor.class);

    List<TLTableFile> tlTableFileDOList2TLTableFileList(List<TLTableFileDO> tlTableFileDOS);

    TLTableFile tlTableFileDO2TLTableFile(TLTableFileDO tlTableFileDO);
}
