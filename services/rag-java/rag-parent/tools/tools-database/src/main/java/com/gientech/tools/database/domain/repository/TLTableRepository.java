package com.gientech.tools.database.domain.repository;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.IService;
import com.gientech.tools.database.domain.entity.TLTable;
import com.gientech.tools.database.domain.model.TLTableDO;

import java.util.List;

public interface TLTableRepository extends IService<TLTableDO> {
    Boolean save(TLTable dbTable);
    Page<TLTable> page(Long databaseId, Long pageNo, Long pageSize);
    List<TLTable> list(Long databaseId);
    TLTable findById(Long id);
    TLTable findByTableName(Long databaseId, String tableName);
    TLTable findByBusinessName(Long databaseId, String businessName);
    Boolean updateById(TLTable dbTable);
    Long countTables(Long databaseId);
    Integer deleteById(Long id);
    Integer deleteByDatabaseId(Long databaseId);
}
