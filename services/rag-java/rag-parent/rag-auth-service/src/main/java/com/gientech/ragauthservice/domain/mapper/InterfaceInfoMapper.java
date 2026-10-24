package com.gientech.ragauthservice.domain.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragauthservice.domain.model.InterfaceInfoDO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

@Mapper
public interface InterfaceInfoMapper extends BaseMapper<InterfaceInfoDO> {

    int saveBatch(@Param("list") List<InterfaceInfoDO> interfaceInfoDOS);

    List<InterfaceInfoDO> listAll();

    Page<InterfaceInfoDO> selectCustomPage(Page<InterfaceInfoDO> page, @Param("fuzzy") String fuzzy);
}