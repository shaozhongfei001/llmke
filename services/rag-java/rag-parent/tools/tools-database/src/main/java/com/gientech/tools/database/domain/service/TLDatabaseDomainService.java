package com.gientech.tools.database.domain.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.tools.database.domain.entity.TLDatabase;
import com.gientech.ragcommon.index.enmus.DataSourceTypeEnum;

import java.util.List;

public interface TLDatabaseDomainService {
    Boolean save(TLDatabase database);
    Boolean updateById(TLDatabase database);
    Page<TLDatabase> page(DataSourceTypeEnum dataSourceTypeEnum, Long pageNo, Long pageSize, String fuzzyWord, String userName, Boolean includingCreator);
    Page<TLDatabase> pageByTargetIds(List<Long> targetIds, Long pageNo, Long pageSize, String fuzzyWord, Boolean includingCreator);
    TLDatabase findById(Long id);
    // 解密后的数据库配置
    TLDatabase findByIdOfDec(Long id);
    Boolean deleteById(Long id);
    Integer getHighestPermission(Long databaseId);
}
