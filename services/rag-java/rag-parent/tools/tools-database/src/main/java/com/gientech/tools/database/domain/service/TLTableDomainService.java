package com.gientech.tools.database.domain.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.tools.database.domain.entity.TLTable;

import java.util.List;

public interface TLTableDomainService {
    Boolean save(TLTable tlTable);
    Page<TLTable> page(Long databaseId, Long pageNo, Long pageSize);
    List<TLTable> list(Long databaseId);
    TLTable findById(Long id);
    TLTable findByTableName(Long databaseId, String tableName);
    TLTable findByBusinessName(Long databaseId, String businessName);
    Boolean updateById(TLTable tlTable);
    Long countTables(Long databaseId);
    Integer deleteById(Long id);
    Integer deleteByDatabaseId(Long databaseId);
}
