package com.gientech.tools.database.application;

import cn.hutool.db.Entity;
import com.gientech.tools.database.domain.entity.TLDatabase;
import com.gientech.ragcommon.index.dto.tools.TLDatabaseDTO;

import java.util.List;

public interface DatabaseBaseService {
    /**
     * 保存数据库配置
     * @param dbDatabase
     * @return
     */
    Long saveDBInfo(TLDatabase dbDatabase);

    /**
     * 查询数据库配置详情
     * @param databaseId
     * @return
     */
    TLDatabaseDTO queryDBInfo(Long databaseId);

    /**
     * 查询数据库中的表数据量
     * @param databaseId
     * @return
     */
    Long totalOfTables(Long databaseId);

    /**
     * 使用sql查询数据
     * @param databaseId
     * @return
     */
    List<Entity> queryData(Long databaseId, String sql);

    /**
     * 删除数据库配置
     * @param databaseId
     * @return
     */
    Boolean deleteDB(Long databaseId);
}
