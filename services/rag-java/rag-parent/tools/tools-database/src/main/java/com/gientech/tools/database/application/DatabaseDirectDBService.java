package com.gientech.tools.database.application;

import com.gientech.tools.database.domain.entity.TLDatabase;
import com.gientech.ragcommon.index.dto.tools.TLTableDataDto;
import com.gientech.tools.database.interfaces.dto.TLTableDto;

import java.util.List;

public interface DatabaseDirectDBService extends DatabaseBaseService {
    /**
     * 测试数据库连接
     * @param dbDatabase
     * @return
     */
    Boolean testConnect(TLDatabase dbDatabase);

    /**
     * 查询数据库中所有的表，不带分页，如果需要分页，可在前端进行分页
     * @param databaseId
     * @return
     */
    List<TLTableDto> pageTableList(Long databaseId);

    /**
     * 查询指定数据库指定表的表和字段详情的元数据
     * @param databaseId
     * @param tableName
     * @return
     */
    TLTableDto queryTableMeta(Long databaseId, String tableName);

    /**
     * 分页查询指定据库指定表的数据
     * @param databaseId
     * @param tableName
     * @param pageNo
     * @param pageSize
     * @return
     */
    TLTableDataDto pageTableData(Long databaseId, String tableName, Long pageNo, Long pageSize);
}
