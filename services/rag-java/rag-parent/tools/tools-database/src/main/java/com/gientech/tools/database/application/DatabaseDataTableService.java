package com.gientech.tools.database.application;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.tools.database.domain.entity.TLTableFile;
import com.gientech.tools.database.infrastructure.calback.ParseFileCallback;
import com.gientech.tools.database.infrastructure.enums.GenDescStatusEnum;
import com.gientech.tools.database.interfaces.dto.ResultDto;
import com.gientech.ragcommon.index.dto.tools.TLTableDataDto;
import com.gientech.tools.database.interfaces.dto.TLTableDto;
import com.gientech.tools.database.interfaces.dto.TLTableFileDTO;
import org.springframework.web.multipart.MultipartFile;

import java.io.InputStream;
import java.util.ArrayDeque;
import java.util.Map;

public interface DatabaseDataTableService extends DatabaseBaseService {

    /**
     * 上传Excel、Csv数据表
     * 将数据存储到实体表中
     *
     * @param tlTableFile
     * @param inputStream
     * @return
     */
    void uploadParseFile(TLTableFile tlTableFile, InputStream inputStream, ParseFileCallback parseFileCallback);

    /**
     * 校验上传的数据文件
     *
     * @param databaseId
     * @param tableId
     * @param tableFile
     * @return
     */
    ResultDto<Boolean> validateTableFile(Long databaseId, Long tableId, MultipartFile tableFile);

    /**
     * 上传单个文件，追加到指定表
     * 如果表头不一致会报错
     *
     * @param tlTableFile
     * @param inputStream
     * @return
     */
    void appendParseFile(TLTableFile tlTableFile, InputStream inputStream);

    /**
     * 数据表分页查询
     *
     * @param databaseId
     * @param pageNo
     * @param pageSize
     * @return
     */
    Page<TLTableDto> pageTableList(Long databaseId, Long pageNo, Long pageSize);

    /**
     * 以文件的形式展示数据表列表
     *
     * @param databaseId
     * @return
     */
    ArrayDeque<TLTableFileDTO> tableFileTreeList(Long databaseId);

    /**
     * 获取单张表的表和字段详情的元数据
     *
     * @param tableId
     * @return
     */
    TLTableDto queryTableMeta(Long tableId);

    /**
     * 获取单张表的表和字段详情的元数据
     *
     * @param tableName
     * @return
     */
    TLTableDto queryTableMetaByTableName(Long databaseId, String tableName);

    /**
     * 更新表信息：表名称、表描述
     *
     * @param tableId
     * @param businessName
     * @param description
     * @return
     */
    Boolean updateTableInfo(Long tableId, String businessName, String description);

    /**
     * 更新表描述
     *
     * @param databaseId
     * @param tableName
     * @return
     */
    Boolean updateTableDescription(Long databaseId, String tableName, String description);

    void updateGenDescErrMsg(Long tableId, String errorMsg);

    void updateGenDescErrMsg(Long databaseId, String tableName, String errorMsg);

    void updateGenDescStatus(Long tableId, GenDescStatusEnum genDescStatus);

    /**
     * 更新字段详情
     *
     * @param columnId
     * @param description
     * @param dataType
     * @return
     */
    Boolean updateColumnInfo(Long columnId, String description, String dataType);

    /**
     * 分页查询单张表的数据
     *
     * @param tableId
     * @param pageNo
     * @param pageSize
     * @return
     */
    TLTableDataDto pageTableData(Long tableId, Long pageNo, Long pageSize);

    /**
     * 以文件为维度，分页查询文件的表数据
     *
     * @param fileId
     * @param pageNo
     * @param pageSize
     * @return
     */
    TLTableDataDto pageTableFileData(Long fileId, Long pageNo, Long pageSize);


    TLTableDataDto pageTableFileDataByTableId(Long databaseId, Long tableId, Long pageNo, Long pageSize);

    /**
     * 更新指定表的指定行数据
     * rowMap中必须带主键编号id
     *
     * @param tableId
     * @param rowMap
     * @return
     */
    Boolean dataUpdateRow(Long tableId, Map<String, String> rowMap);

    /**
     * 删除指定表的指定行数据
     *
     * @param tableId
     * @param rowId
     * @return
     */
    Boolean dataDeleteRow(Long tableId, Long rowId);

    /***
     * 删除指定表
     * @param tableId
     * @return
     */
    Boolean deleteTable(Long tableId);

    /**
     * 删除数据表中fileId对应文件数据
     *
     * @param fileId
     * @return
     */
    Boolean deleteTableFileData(Long fileId);
}
