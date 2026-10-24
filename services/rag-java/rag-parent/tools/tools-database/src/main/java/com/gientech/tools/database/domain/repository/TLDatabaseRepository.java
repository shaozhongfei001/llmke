package com.gientech.tools.database.domain.repository;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.IService;
import com.gientech.tools.database.domain.entity.TLDatabase;
import com.gientech.tools.database.domain.model.TLDatabaseDO;
import com.gientech.ragcommon.index.enmus.DataSourceTypeEnum;

import java.util.List;

public interface TLDatabaseRepository extends IService<TLDatabaseDO> {
    Boolean save(TLDatabase dbDatabase);
    Page<TLDatabase> page(DataSourceTypeEnum dataSourceTypeEnum, Long pageNo, Long pageSize, String fuzzyWord, String userName, Boolean includingCreator);
    Page<TLDatabase> pageByTargetIds(List<Long> targetIds, Long pageNo, Long pageSize, String fuzzyWord, Boolean includingCreator);
    TLDatabase findById(Long id);
    Boolean updateById(TLDatabase dbDatabase);
    Integer getHighestPermission(Long databaseId, Long deptId, Long userId, String userName);
}
