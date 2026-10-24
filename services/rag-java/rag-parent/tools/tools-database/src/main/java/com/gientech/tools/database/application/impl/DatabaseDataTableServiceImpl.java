package com.gientech.tools.database.application.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.io.FileUtil;
import cn.hutool.core.io.IoUtil;
import cn.hutool.core.io.file.FileNameUtil;
import cn.hutool.core.lang.Assert;
import cn.hutool.core.text.csv.CsvData;
import cn.hutool.core.text.csv.CsvReader;
import cn.hutool.core.text.csv.CsvRow;
import cn.hutool.core.text.csv.CsvUtil;
import cn.hutool.core.util.CharsetUtil;
import cn.hutool.core.util.StrUtil;
import cn.hutool.db.Db;
import cn.hutool.db.DbUtil;
import cn.hutool.db.Entity;
import cn.hutool.db.PageResult;
import cn.hutool.db.handler.EntityListHandler;
import cn.hutool.db.meta.Column;
import cn.hutool.db.meta.MetaUtil;
import cn.hutool.db.meta.Table;
import cn.hutool.db.sql.SqlExecutor;
import cn.hutool.poi.excel.ExcelReader;
import cn.hutool.poi.excel.ExcelUtil;
import cn.hutool.poi.excel.sax.handler.RowHandler;
import com.alibaba.excel.util.StringUtils;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.index.dto.tools.TLDatabaseDTO;
import com.gientech.ragcommon.index.dto.tools.TLTableColumnDto;
import com.gientech.ragcommon.index.dto.tools.TLTableDataDto;
import com.gientech.ragcommon.index.enmus.DataSourceTypeEnum;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.tools.database.application.DatabaseDataTableService;
import com.gientech.tools.database.application.remote.DatabaseConfigClient;
import com.gientech.tools.database.application.remote.DatabasePermissionService;
import com.gientech.tools.database.domain.entity.TLDatabase;
import com.gientech.tools.database.domain.entity.TLTable;
import com.gientech.tools.database.domain.entity.TLTableColumn;
import com.gientech.tools.database.domain.entity.TLTableFile;
import com.gientech.tools.database.domain.service.TLDatabaseDomainService;
import com.gientech.tools.database.domain.service.TLTableColumnDomainService;
import com.gientech.tools.database.domain.service.TLTableDomainService;
import com.gientech.tools.database.domain.service.TLTableFileDomainService;
import com.gientech.tools.database.infrastructure.calback.ParseFileCallback;
import com.gientech.tools.database.infrastructure.converter.TLDatabaseConverter;
import com.gientech.tools.database.infrastructure.enums.FileParseStatusEnum;
import com.gientech.tools.database.infrastructure.enums.GenDescStatusEnum;
import com.gientech.tools.database.infrastructure.util.EncodingConverterUtil;
import com.gientech.tools.database.infrastructure.util.EsUtil;
import com.gientech.tools.database.infrastructure.util.ExcelToMysqlUtil;
import com.gientech.tools.database.infrastructure.util.WorkbookRowReader;
import com.gientech.tools.database.interfaces.dto.ResultDto;
import com.gientech.tools.database.interfaces.dto.TLTableDto;
import com.gientech.tools.database.interfaces.dto.TLTableFileDTO;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import javax.sql.DataSource;
import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.sql.Connection;
import java.sql.SQLException;
import java.util.*;
import java.util.concurrent.atomic.AtomicReference;
import java.util.stream.Collectors;

import static com.gientech.ragcommon.qa.constant.AIConstant.DB_PREFIX;

@Slf4j
@Service
public class DatabaseDataTableServiceImpl implements DatabaseDataTableService {
    @Autowired
    private TLDatabaseDomainService tlDatabaseDomainService;
    @Autowired
    private TLTableDomainService tlTableDomainService;
    @Autowired
    private TLTableFileDomainService tlTableFileDomainService;
    @Autowired
    private TLTableColumnDomainService tlTableColumnDomainService;
    @Autowired
    private DatabasePermissionService databasePermissionService;
    @Autowired
    private JdbcTemplate jdbcTemplate;
    @Autowired
    private DatabaseConfigClient databaseConfigClient;
    @Autowired
    private EsUtil esUtil;


    // 表名称前缀
    private final String DATA_TABLE_PREFIX = "tools_table_";

    // 批量插入行数设置
    private final int BATCH_INSERT_ROW = 1000;

    // 数据表，默认字段
    private String[] defaultFields = {"id", "file_id"};


    @Override
    public Long saveDBInfo(TLDatabase tlDatabase) {
        tlDatabase.setDatasourceType(DataSourceTypeEnum.DataTable.getCode());
        if (tlDatabase.getId() != null) {
            TLDatabase originalDatabase = tlDatabaseDomainService.findById(tlDatabase.getId());
            String originalName = originalDatabase.getName();
            String dbIndex = DB_PREFIX + tlDatabase.getId();
            tlDatabaseDomainService.updateById(tlDatabase);
            updateSearchConfig(tlDatabase.getName(), originalName, dbIndex);
        } else {
            tlDatabaseDomainService.save(tlDatabase);
        }

        return tlDatabase.getId();
    }

    private void updateSearchConfig(String updatedName, String originalName, String dbIndex) {
        if (StringUtils.isNotBlank(updatedName) && !originalName.equals(updatedName)) {
            //更新配置助手
            databaseConfigClient.renameDbIndex(dbIndex, updatedName, originalName);
        }
    }

    @Override
    public TLDatabaseDTO queryDBInfo(Long databaseId) {
        TLDatabase tlDatabase = tlDatabaseDomainService.findById(databaseId);
        Assert.notNull(tlDatabase, "数据库配置不存在");
        TLDatabaseDTO tlDatabaseDTO = TLDatabaseConverter.INSTANCE.convert(tlDatabase);


        tlDatabaseDTO.setPermission(tlDatabaseDomainService.getHighestPermission(databaseId));
        return tlDatabaseDTO;
    }

    @Override
    public Long totalOfTables(Long databaseId) {
        return tlTableDomainService.countTables(databaseId);
    }

    @Override
    public List<Entity> queryData(Long databaseId, String sql) {
        Assert.isTrue(sql.contains(DATA_TABLE_PREFIX) || sql.contains(DATA_TABLE_PREFIX.toUpperCase()),
                "数据表类型的数据库查询仅支持该范围内的数据表查询");
        DataSource dataSource = jdbcTemplate.getDataSource();
        Connection connection = null;
        List<Entity> entityList = new ArrayList<>();
        try {
            connection = dataSource.getConnection();
            entityList = SqlExecutor.query(connection, sql, new EntityListHandler());
        } catch (SQLException e) {
            throw new RuntimeException("SQL执行出错", e);
        } finally {
            DbUtil.close(connection);
        }

        return entityList;
    }

    @Async("asyncExecutor")
    @Override
    public void uploadParseFile(TLTableFile tlTableFile, InputStream inputStream, ParseFileCallback parseFileCallback) {
        try (inputStream) {
            // 记录解析耗时，开始时间
            long startTime = System.currentTimeMillis();


            Long tableId = tlTableFile.getTableId();

            // 设置解析状态
            tlTableFile.setStatus(FileParseStatusEnum.S11.getCode());
            tlTableFileDomainService.updateById(tlTableFile);

            Long databaseId = tlTableFile.getDatabaseId();
            String originalFilename = tlTableFile.getOriginalFilename();
            String extName = FileNameUtil.extName(originalFilename).toLowerCase();

            TLTable tlTable = tlTableDomainService.findById(tableId);
            String tablePhysicalName = DATA_TABLE_PREFIX.concat(String.valueOf(tableId));
            tlTable.setPhysicalName(tablePhysicalName);
            tlTableDomainService.updateById(tlTable);

            if (extName.equals("xlsx")) {
                WorkbookRowReader.read(inputStream, 0, excelRowHandler(tlTableFile, tlTable, true));
            } else if (extName.equals("xls")) {
                WorkbookRowReader.read(inputStream, 0, excelRowHandler(tlTableFile, tlTable, true));
            } else if (extName.equals("csv")) {
                // 自动转化成UTF-8，支持GBK等格式数据导入
                try (InputStream inputStreamNew = EncodingConverterUtil.convertToUTF8Stream(inputStream, CharsetUtil.UTF_8)) {
                    csvHandler(inputStreamNew, tlTableFile, tlTable, true);
                }
            } else {
                tlTableFile.setStatus(FileParseStatusEnum.S00.getCode());
                tlTableFileDomainService.updateById(tlTableFile);
                throw new RuntimeException("不支持该文件格式");
            }

            DataSource dataSource = jdbcTemplate.getDataSource();

            // 获取字段数量
            Table tableMeta = MetaUtil.getTableMeta(dataSource, tablePhysicalName);
            Collection<Column> columns = tableMeta.getColumns();
            Assert.isFalse(tableMeta.getComment() == null && columns.isEmpty(), "数据表:{}疑似不存在", tablePhysicalName);
            tlTable.setColumnCount(columns.size());

            // 获取数据量
            Long rowCount = jdbcTemplate.queryForObject("SELECT COUNT(1) FROM " + tablePhysicalName, Long.class);
            tlTable.setRowCount(rowCount);

            tlTableDomainService.updateById(tlTable);

            // 存储所有的字段
            List<TLTableColumn> tlTableColumns = new ArrayList<>();
            for (Column column : columns) {
                TLTableColumn tlTableColumn = new TLTableColumn();
                tlTableColumn.setDatabaseId(databaseId);
                tlTableColumn.setTableId(tableId);

                String name = column.getName();
                String comment = column.getComment();
                String typeName = column.getTypeName();
                tlTableColumn.setPhysicalName(name);
                tlTableColumn.setBusinessName(comment);
                tlTableColumn.setDataType(typeName);

                tlTableColumns.add(tlTableColumn);
            }
            tlTableColumnDomainService.batchSave(tlTableColumns);

            // 记录结束时间
            long endTime = System.currentTimeMillis();
            // 计算耗时（毫秒）
            long useTime = endTime - startTime;

            tlTableFile.setTableId(tableId);
            tlTableFile.setStatus(FileParseStatusEnum.S30.getCode());
            tlTableFile.setUseTime(useTime);
            tlTableFileDomainService.updateById(tlTableFile);

            // 异步回调
            if (parseFileCallback != null) {
                TLTable rstTlTable = tlTableDomainService.findById(tableId);
                parseFileCallback.onComplete(rstTlTable);
            }
        } catch (Exception e) {
            String errorMsg = StrUtil.sub(e.getMessage(), 0, 900);
            tlTableFile.setStatus(FileParseStatusEnum.S00.getCode());
            tlTableFile.setErrorMsg(errorMsg);
            tlTableFileDomainService.updateById(tlTableFile);
            log.error("文件解析出错", e);
        }
    }

    @Override
    public ResultDto<Boolean> validateTableFile(Long databaseId, Long tableId, MultipartFile tableFile) {
        ResultDto<Boolean> resultDto = new ResultDto<>();
        resultDto.setData(true);

        String originalFilename = tableFile.getOriginalFilename();
        String prefixName = FileNameUtil.getPrefix(originalFilename);
        String extName = Objects.requireNonNull(FileNameUtil.extName(originalFilename)).toLowerCase();

        if (tableId == null) {
            // 首次上传校验
            TLTable tlTable = tlTableDomainService.findByBusinessName(databaseId, prefixName);
            if (tlTable != null) {
                resultDto.setMessage("该数据库中已存在同名的数据表");
                resultDto.setData(false);
                return resultDto;
            }
        }


        List<String> tableHeader = new ArrayList<>();
        int rowCount = 0;

        try {
            byte[] data = IoUtil.readBytes(tableFile.getInputStream());
            if (extName.equals("xls") || extName.equals("xlsx")) {
                try {
                    ExcelReader reader = ExcelUtil.getReader(new ByteArrayInputStream(data));
                    int sheetCount = reader.getSheetCount();
                    if (sheetCount > 1) {
                        throw new ApplicationException(ErrCodeEnum.DATA_TABLE_EXCEL_MULTI_SHEET);
                    }
                    rowCount = reader.getRowCount();
                    if (rowCount > 0) {
                        List<Object> headers = reader.readRow(0);
                        tableHeader = headers.stream()
                                .map(obj -> obj != null ? obj.toString() : null)
                                .collect(Collectors.toList());
                    } else {
                        resultDto.setMessage("上传表格文件，行数为0！");
                        resultDto.setData(false);
                        return resultDto;
                    }

                    reader.close();
                } catch (ApplicationException e) {
                    throw e;
                } catch (Exception e) {
                    resultDto.setMessage("EXCEL文件解析异常");
                    resultDto.setData(false);
                    log.error("EXCEL文件解析异常", e);
                    return resultDto;
                }
            } else if (extName.equals("csv")) {
                try {
                    File tempFile = FileUtil.createTempFile("database", ".csv", true);
                    FileUtil.writeFromStream(new ByteArrayInputStream(data), tempFile);

                    CsvReader reader = CsvUtil.getReader();
                    CsvData csvData = reader.read(tempFile);

                    rowCount = csvData.getRowCount();

                    if (rowCount > 0) {
                        CsvRow row = csvData.getRow(0);
                        tableHeader = row.getRawList();
                    } else {
                        resultDto.setMessage("上传表格文件，行数为0！");
                        resultDto.setData(false);
                        return resultDto;
                    }

                    reader.close();
                    FileUtil.del(tempFile);
                } catch (IOException e) {
                    resultDto.setMessage("CSV文件解析异常");
                    resultDto.setData(false);
                    log.error("EXCEL文件解析异常", e);
                    return resultDto;
                }
            } else {
                resultDto.setMessage("不支持该文件格式");
                resultDto.setData(false);
                return resultDto;
            }
        } catch (IOException e) {
            resultDto.setMessage("文件读取异常");
            resultDto.setData(false);
            log.error("文件读取异常", e);
            return resultDto;
        }

        if (rowCount > 100000) {
            resultDto.setMessage("上传表格文件，数据行数不能大于10万！");
            resultDto.setData(false);
            return resultDto;
        }

        if (tableId == null) {
            // 首次上传校验
            if (tableHeader == null || tableHeader.size() == 0) {
                resultDto.setMessage("上传表格文件，表头为空！");
                resultDto.setData(false);
                return resultDto;
            } else {
                int size = tableHeader.size();
                if (size > 60) {
                    resultDto.setMessage("上传表格文件，列数不能大于60列！");
                    resultDto.setData(false);
                    return resultDto;
                }
            }
        } else {
            // 追加上传校验
            TLTableDto tlTableDto = queryTableMeta(tableId);
            List<TLTableColumnDto> columns = tlTableDto.getColumns();

            // 移除默认字段
            for (int i = 0; i < columns.size(); i++) {
                TLTableColumnDto tlTableColumnDto = columns.get(i);
                String physicalName = tlTableColumnDto.getPhysicalName();
                for (String defaultField : defaultFields) {
                    if (defaultField.equals(physicalName)) {
                        columns.remove(tlTableColumnDto);
                    }
                }
            }

            if (tableHeader.size() != columns.size()) {
                resultDto.setMessage("数据表列数不匹配");
                resultDto.setData(false);
                return resultDto;
            }
            Boolean columnNameValid = true;
            for (int i = 0; i < columns.size(); i++) {
                TLTableColumnDto tlTableColumnDto = columns.get(i);
                String businessName = tlTableColumnDto.getBusinessName();
                String tableHeaderName = tableHeader.get(i);
                if (!businessName.equals(tableHeaderName)) {
                    columnNameValid = false;
                }

            }
            if (!columnNameValid) {
                resultDto.setMessage("数据表列名称不匹配");
                resultDto.setData(false);
                return resultDto;
            }
        }

        Map<String, Object> map = new HashMap<>();
        map.put("columnCount", tableHeader.size());
        map.put("rowCount", rowCount);
        resultDto.setExtra(map);

        return resultDto;
    }

    @Async
    @Override
    public void appendParseFile(TLTableFile tlTableFile, InputStream inputStream) {
        try (inputStream) {
            // 记录解析耗时，开始时间
            long startTime = System.currentTimeMillis();

            // 自动转化成UTF-8，支持GBK等格式数据导入


            // 设置解析状态
            tlTableFile.setStatus(FileParseStatusEnum.S11.getCode());
            tlTableFileDomainService.updateById(tlTableFile);

            String fileName = tlTableFile.getOriginalFilename();
            String extName = FileNameUtil.extName(fileName).toLowerCase();
            Long tableId = tlTableFile.getTableId();

            TLTable tlTable = tlTableDomainService.findById(tableId);
            Assert.notNull(tlTable, "数据表：{}不存在", tableId);

            if (extName.equals("xlsx")) {
                WorkbookRowReader.read(inputStream, 0, excelRowHandler(tlTableFile, tlTable, false));
            } else if (extName.equals("xls")) {
                WorkbookRowReader.read(inputStream, 0, excelRowHandler(tlTableFile, tlTable, false));
            } else if (extName.equals("csv")) {
                try (InputStream inputStreamNew = EncodingConverterUtil.convertToUTF8Stream(inputStream, CharsetUtil.UTF_8);) {
                    csvHandler(inputStreamNew, tlTableFile, tlTable, false);
                }
            } else {
                tlTableFile.setStatus(FileParseStatusEnum.S00.getCode());
                tlTableFileDomainService.updateById(tlTableFile);
                throw new RuntimeException("不支持该文件格式");
            }

            String tablePhysicalName = tlTable.getPhysicalName();

            // 获取数据量
            Long rowCount = jdbcTemplate.queryForObject("SELECT COUNT(1) FROM " + tablePhysicalName, Long.class);
            tlTable.setRowCount(rowCount);

            tlTableDomainService.updateById(tlTable);

            // 记录结束时间
            long endTime = System.currentTimeMillis();
            // 计算耗时（毫秒）
            long useTime = endTime - startTime;

            tlTableFile.setStatus(FileParseStatusEnum.S30.getCode());
            tlTableFile.setUseTime(useTime);
            tlTableFileDomainService.updateById(tlTableFile);
        } catch (Exception e) {
            String errorMsg = StrUtil.sub(e.getMessage(), 0, 900);
            tlTableFile.setStatus(FileParseStatusEnum.S00.getCode());
            tlTableFile.setErrorMsg(errorMsg);
            tlTableFileDomainService.updateById(tlTableFile);
            throw new RuntimeException("EXCEL文件解析异常", e);
        }
    }

    /**
     * 处理excel单行数据
     *
     * @param tlTable
     * @return
     */
    private RowHandler excelRowHandler(TLTableFile tlTableFile, TLTable tlTable, Boolean isNewTable) {
        log.info("excelRowHandler....");
        String tableComment = tlTable.getBusinessName();
        String tableName = tlTable.getPhysicalName();
        Long fileId = tlTableFile.getId();

        AtomicReference<String> insertSqlAr = new AtomicReference<>();
        AtomicReference<List<Object[]>> insertRowsAr = new AtomicReference<>();

        return new RowHandler() {
            @Override
            public void handle(int sheetIndex, long rowIndex, List<Object> rowCells) {
                log.info("handler....");
                if (rowIndex == 0) {
                    if (isNewTable) {
                        String createTableSql = ExcelToMysqlUtil.generateCreateTableSql(tableName, tableComment, rowCells);
                        log.debug("生成建表语句", createTableSql);
                        jdbcTemplate.execute(createTableSql);
                    }

                    String insertSql = ExcelToMysqlUtil.buildInsertSql(tableName, fileId, rowCells.size());
                    insertSqlAr.set(insertSql);
                    insertRowsAr.set(new ArrayList<>());
                    tlTableFile.setStatus(FileParseStatusEnum.S20.getCode());
                    tlTableFileDomainService.updateById(tlTableFile);
                } else {
                    List<Object[]> insertBathArgs = insertRowsAr.get();
                    insertBathArgs.add(rowCells.toArray());
                    insertRowsAr.set(insertBathArgs);

                    if (rowIndex % BATCH_INSERT_ROW == 0) {
                        String insertSql = insertSqlAr.get();
                        List<Object[]> insertBathArgsTmp = insertRowsAr.get();

                        jdbcTemplate.batchUpdate(insertSql, insertBathArgsTmp);
                        insertRowsAr.set(new ArrayList<>());
                    }
                }
            }

            @Override
            public void doAfterAllAnalysed() {
                RowHandler.super.doAfterAllAnalysed();

                String insertSql = insertSqlAr.get();
                List<Object[]> insertBathArgsFinally = insertRowsAr.get();

                jdbcTemplate.batchUpdate(insertSql, insertBathArgsFinally);
                insertRowsAr.set(new ArrayList<>());
            }
        };
    }

    /**
     * 处理csv文件
     *
     * @param inputStream
     * @param tlTable
     * @return
     * @throws IOException
     */
    private void csvHandler(InputStream inputStream, TLTableFile tlTableFile, TLTable tlTable, Boolean isNewTable) throws IOException {
        String physicalName = tlTable.getPhysicalName();
        String businessName = tlTable.getBusinessName();
        Long fileId = tlTableFile.getId();

        File tempFile = FileUtil.createTempFile("database", ".csv", true);
        FileUtil.writeFromStream(inputStream, tempFile);

        CsvReader reader = CsvUtil.getReader();
        CsvData csvData = reader.read(tempFile);

        String insertSql = null;
        List<Object[]> rowDataList = new ArrayList<>();

        List<CsvRow> rows = csvData.getRows();
        for (int i = 0; i < rows.size(); i++) {
            CsvRow csvRow = rows.get(i);
            List<String> rawList = csvRow.getRawList();
            List<Object> rowCells = rawList.stream()
                    .map(s -> (Object) ExcelToMysqlUtil.truncateContent(s, 200))
                    .collect(Collectors.toList());
            if (i == 0) {
                if (isNewTable) {
                    String createTableSql = ExcelToMysqlUtil.generateCreateTableSql(physicalName, businessName, rowCells);
                    log.debug("生成建表语句", createTableSql);
                    jdbcTemplate.execute(createTableSql);
                }
                insertSql = ExcelToMysqlUtil.buildInsertSql(physicalName, fileId, rowCells.size());
                tlTableFile.setStatus(FileParseStatusEnum.S20.getCode());
                tlTableFileDomainService.updateById(tlTableFile);
            } else {
                rowDataList.add(rowCells.toArray());

                if (i % BATCH_INSERT_ROW == 0) {
                    jdbcTemplate.batchUpdate(insertSql, rowDataList);
                    rowDataList = new ArrayList<>();
                }
            }
        }

        if (rowDataList.size() > 0) {
            jdbcTemplate.batchUpdate(insertSql, rowDataList);
        }
        reader.close();
        FileUtil.del(tempFile);
    }


    @Override
    public Page<TLTableDto> pageTableList(Long databaseId, Long pageNo, Long pageSize) {
        pageNo = Objects.isNull(pageNo) ? 1 : pageNo;
        pageSize = Objects.isNull(pageSize) ? 10 : pageSize;

        Page<TLTableDto> rstPage = new Page<>();
        Page<TLTable> page = tlTableDomainService.page(databaseId, pageNo, pageSize);
        BeanUtil.copyProperties(page, rstPage);
        return rstPage;
    }

    @Override
    public ArrayDeque<TLTableFileDTO> tableFileTreeList(Long databaseId) {
        List<TLTableFile> tableFileList = tlTableFileDomainService.findImportedByDatabaseId(databaseId);

        // 获取数据库权限
        Integer permission = tlDatabaseDomainService.getHighestPermission(databaseId);

        // 1. 使用tableId进行分组
        // 过滤掉不存在tableId的数据，例如：未解析等
        LinkedHashMap<Long, List<TLTableFile>> groupedByTableId = tableFileList.stream()
                .filter(tlTableFile -> tlTableFile.getTableId() != null)
                .sorted(Comparator.comparing(TLTableFile::getGmtCreate))
                .collect(Collectors.groupingBy(
                        TLTableFile::getTableId,
                        LinkedHashMap::new,
                        Collectors.collectingAndThen(
                                Collectors.toList(),
                                list -> list.stream()
                                        .sorted(Comparator.comparing(TLTableFile::getGmtCreate))
                                        .collect(Collectors.toList())
                        )
                ));

        ArrayDeque<TLTableFileDTO> rootNodes = new ArrayDeque<>();

        // 2. 处理每个分组
        for (Map.Entry<Long, List<TLTableFile>> entry : groupedByTableId.entrySet()) {
            List<TLTableFile> tableFiles = entry.getValue();
            Long mainTableId = entry.getKey();
            //删除待导入状态的追加文件
            tlTableFileDomainService.deleteByTableId(mainTableId, FileParseStatusEnum.S10.getCode());

            // 3. 按创建时间排序，最早的排在前面
//            List<TLTableFile> sortedRecords = tableFiles.stream()
//                    .sorted(Comparator.comparing(TLTableFile::getGmtCreate).reversed())
//                    .toList();

            // 4. 第一条记录（最早的）作为父节点（第一层）
            TLTableFile firstRecord = tableFiles.get(0);

            TLTableFileDTO parentTableFileDto = BeanUtil.copyProperties(firstRecord, TLTableFileDTO.class);
            parentTableFileDto.setFileId(firstRecord.getId());
            parentTableFileDto.setPermission(permission);

            if (firstRecord.isCreatedTable()) {
                Long tableId = parentTableFileDto.getTableId();
                TLTableDto tlTableDto = queryTableMeta(tableId);
                parentTableFileDto.setTableMeta(tlTableDto);
            }

            // 5. 其余记录作为子节点（第二层）
            for (int i = 1; i < tableFiles.size(); i++) {
                TLTableFile tlTableFile = tableFiles.get(i);
                TLTableFileDTO childTableFileDto = BeanUtil.copyProperties(tlTableFile, TLTableFileDTO.class);
                childTableFileDto.setFileId(tlTableFile.getId());
                childTableFileDto.setPermission(permission);
                parentTableFileDto.setPermission(permission);

                parentTableFileDto.addChild(childTableFileDto);
            }

            // 6. 将父节点添加到根节点列表
            rootNodes.push(parentTableFileDto);
        }

        return rootNodes;
    }


    @Override
    public TLTableDto queryTableMeta(Long tableId) {
        TLTable tlTable = tlTableDomainService.findById(tableId);
        Assert.notNull(tlTable, "数据表：{}不存在", tableId);

        String physicalName = tlTable.getPhysicalName();

        DataSource dataSource = jdbcTemplate.getDataSource();

        TLTableDto tlTableDto = new TLTableDto();
        BeanUtil.copyProperties(tlTable, tlTableDto);


        Map<String, List<String>> sampleValueMap = new HashMap<>();
        try {

            Entity entityWhere = new Entity();
            entityWhere.setTableName(physicalName);
            PageResult<Entity> pageTableData = Db.use(dataSource).page(entityWhere, 0, 3);
            for (Entity entity : pageTableData) {
                Set<String> fieldNames = entity.getFieldNames();
                for (String fieldName : fieldNames) {
                    Object sampleValueObj = entity.get(fieldName);
                    String sampleValue = sampleValueObj == null ? "" : sampleValueObj.toString();

                    List<String> sampleValueList = sampleValueMap.get(fieldName);
                    if (null == sampleValueList) {
                        sampleValueList = new ArrayList<>();
                    }
                    sampleValueList.add(sampleValue);
                    sampleValueMap.put(fieldName, sampleValueList);
                }
            }
        } catch (SQLException e) {
            log.error("查询数据表发生错误", e);
            throw new RuntimeException(e);
        }

        List<TLTableColumn> tlTableColumns = tlTableColumnDomainService.listByTableId(tableId, false);
        tlTableDto.setColumnCount(tlTableColumns.size());

        List<TLTableColumnDto> tlTableColumnDtos = BeanUtil.copyToList(tlTableColumns, TLTableColumnDto.class);

        for (TLTableColumnDto tlTableColumnDto : tlTableColumnDtos) {
            String columnName = tlTableColumnDto.getPhysicalName();
            tlTableColumnDto.setSampleValues(sampleValueMap.get(columnName));
        }
        tlTableDto.setColumns(tlTableColumnDtos);

        return tlTableDto;
    }

    @Override
    public TLTableDto queryTableMetaByTableName(Long databaseId, String tableName) {
        TLTable tlTable = tlTableDomainService.findByTableName(databaseId, tableName);
        Assert.notNull(tlTable, "数据表：{}不存在", tableName);

        return queryTableMeta(tlTable.getId());
    }


    @Override
    public Boolean updateTableInfo(Long tableId, String businessName, String description) {
        TLTable tlTable = tlTableDomainService.findById(tableId);
        Assert.notNull(tlTable, "数据表：{}不存在", tableId);
        if (businessName != null && !"".equals(businessName)) {
            tlTable.setBusinessName(businessName);
        }
        if (description != null && !"".equals(description)) {
            tlTable.setDescription(description);
        }
        Boolean rst = tlTableDomainService.updateById(tlTable);

        String physicalName = tlTable.getPhysicalName();
        String sql = "ALTER TABLE " + physicalName + " COMMENT '" + businessName + "'";
        jdbcTemplate.execute(sql);

        return rst;
    }

    @Override
    public Boolean updateTableDescription(Long databaseId, String tableName, String description) {
        TLTable tlTable = tlTableDomainService.findByTableName(databaseId, tableName);
        tlTable.setDescription(description);
        tlTable.setGenDescStatus(GenDescStatusEnum.SUCCESS.getStatus());
        return tlTableDomainService.updateById(tlTable);
    }

    @Override
    public void updateGenDescErrMsg(Long tableId, String errorMsg) {
        TLTable tlTable = new TLTable();
        tlTable.setId(tableId);
        tlTable.setGenDescErrMsg(errorMsg);
        tlTable.setGenDescStatus(GenDescStatusEnum.FAIL.getStatus());
        tlTableDomainService.updateById(tlTable);
    }

    @Override
    public void updateGenDescErrMsg(Long databaseId, String tableName, String errorMsg) {
        TLTable tlTable = tlTableDomainService.findByTableName(databaseId, tableName);
        tlTable.setGenDescErrMsg(errorMsg);
        tlTable.setGenDescStatus(GenDescStatusEnum.FAIL.getStatus());
        tlTableDomainService.updateById(tlTable);
    }

    @Override
    public void updateGenDescStatus(Long tableId, GenDescStatusEnum genDescStatus) {
        TLTable tlTable = new TLTable();
        tlTable.setId(tableId);
        tlTable.setGenDescStatus(genDescStatus.getStatus());
        tlTableDomainService.updateById(tlTable);
    }

    @Override
    public Boolean updateColumnInfo(Long columnId, String description, String dataType) {
        TLTableColumn tlTableColumn = tlTableColumnDomainService.findById(columnId);
        if (description != null && !"".equals(description)) {
            tlTableColumn.setDescription(description);
        }
        if (dataType != null && !"".equals(dataType)) {
            tlTableColumn.setDataType(dataType);
        }
        return true;
    }

    @Override
    public TLTableDataDto pageTableData(Long tableId, Long pageNo, Long pageSize) {
        TLTable tlTable = tlTableDomainService.findById(tableId);
        Assert.notNull(tlTable, "数据表：{}不存在", tableId);

        Long databaseId = tlTable.getDatabaseId();
        // 获取数据库权限
        Integer permission = databasePermissionService.queryDatabasePermission(databaseId);

        TLTableDataDto tlTableDataDto = queryTableData(tableId, pageNo, pageSize, null, false);
        tlTableDataDto.setPermission(permission);

        return tlTableDataDto;
    }

    @Override
    public TLTableDataDto pageTableFileData(Long fileId, Long pageNo, Long pageSize) {
        TLTableFile tlTableFile = tlTableFileDomainService.findById(fileId);
        Assert.notNull(tlTableFile, "数据表文件：{}不存在", fileId);
        String status = tlTableFile.getStatus();
        Assert.isTrue(FileParseStatusEnum.S30.getCode().equals(status), "数据表文件：{}尚未完成导入", fileId);

        Long tableId = tlTableFile.getTableId();

        Map<String, Object> eqWhere = new HashMap<>();
        eqWhere.put("file_id", fileId);

        Long databaseId = tlTableFile.getDatabaseId();
        // 获取数据库权限
        Integer permission = tlDatabaseDomainService.getHighestPermission(databaseId);

        TLTableDataDto tlTableDataDto = queryTableData(tableId, pageNo, pageSize, eqWhere, false);
        tlTableDataDto.setPermission(permission);

        return tlTableDataDto;
    }


    @Override
    public TLTableDataDto pageTableFileDataByTableId(Long databaseId, Long tableId, Long pageNo, Long pageSize) {
        TLTableFile tlTableFile = tlTableFileDomainService.findByTableIdAndDatabaseId(tableId, databaseId);
        Long fileId = tlTableFile.getId();
        Map<String, Object> eqWhere = new HashMap<>();
        eqWhere.put("file_id", fileId);
        // 获取数据库权限
        Integer permission = tlDatabaseDomainService.getHighestPermission(databaseId);
        TLTableDataDto tlTableDataDto = queryTableData(tableId, pageNo, pageSize, eqWhere, false);
        tlTableDataDto.setPermission(permission);
        tlTableDataDto.setFileId(fileId);

        return tlTableDataDto;
    }

    /**
     * @param tableId
     * @param pageNo
     * @param pageSize
     * @param eqWhere
     * @param isHaveDefField 查询结果是否包含默认字段
     * @return
     */
    private TLTableDataDto queryTableData(Long tableId, Long pageNo, Long pageSize, Map<String, Object> eqWhere, Boolean isHaveDefField) {
        TLTable tlTable = tlTableDomainService.findById(tableId);
        Assert.notNull(tlTable, "数据表：{}不存在", tableId);

        String physicalName = tlTable.getPhysicalName();

        pageNo = Objects.isNull(pageNo) ? 1 : pageNo;
        pageSize = Objects.isNull(pageSize) ? 10 : pageSize;

        DataSource dataSource = jdbcTemplate.getDataSource();
        TLTableDataDto tlTableDataDto = new TLTableDataDto();
        tlTableDataDto.setTableName(physicalName);

        TLTableDto tlTableDto = queryTableMeta(tableId);
        tlTableDataDto.setColumns(tlTableDto.getColumns());
        try {
            Entity entityWhere = new Entity();
            entityWhere.setTableName(physicalName);

            if (eqWhere != null && !eqWhere.isEmpty()) {
                for (Map.Entry<String, Object> entry : eqWhere.entrySet()) {
                    String column = entry.getKey();
                    Object value = entry.getValue();

                    entityWhere.set(column, value);
                }
            }

            PageResult<Entity> pageTableData = Db.use(dataSource).page(entityWhere, pageNo.intValue() - 1, pageSize.intValue());

            if (!isHaveDefField) {
                for (Entity entity : pageTableData) {
                    entity.remove("file_id");
                }
            }

            int totalPage = pageTableData.getTotalPage();
            int dataPage = pageTableData.getPage();
            int dataPageSize = pageTableData.getPageSize();
            int total = pageTableData.getTotal();
            tlTableDataDto.setTotalPage(totalPage);
            tlTableDataDto.setPageNo(dataPage + 1);
            tlTableDataDto.setPageSize(dataPageSize);
            tlTableDataDto.setTotalData(total);

            tlTableDataDto.setDataList(pageTableData);
        } catch (SQLException e) {
            log.error("查询数据表发生错误", e);
            throw new RuntimeException(e);
        }
        return tlTableDataDto;
    }


    @Override
    public Boolean dataUpdateRow(Long tableId, Map<String, String> rowMap) {
        String id = rowMap.get("id");
        Assert.notNull(id, "未传入主键，无法进行更新！");

        TLTable tlTable = tlTableDomainService.findById(tableId);
        Assert.notNull(tlTable, "数据表：{}不存在", tableId);

        String physicalName = tlTable.getPhysicalName();
        Entity updateEntity = Entity.create(physicalName);

        Set<Map.Entry<String, String>> entrySet = rowMap.entrySet();
        for (Map.Entry<String, String> entry : entrySet) {
            String key = entry.getKey();

            if (!"id".equals(key)) {
                String value = entry.getValue();
                updateEntity.set(key, value);
            }

        }

        DataSource dataSource = jdbcTemplate.getDataSource();

        Entity whereEntity = new Entity();
        whereEntity.set("id", id);
        try {
            int rows = Db.use(dataSource).update(updateEntity, whereEntity);
        } catch (SQLException e) {
            throw new RuntimeException("更新行数据出错", e);
        }

        return true;
    }

    @Override
    public Boolean dataDeleteRow(Long tableId, Long rowId) {
        TLTable tlTable = tlTableDomainService.findById(tableId);
        Assert.notNull(tlTable, "数据表：{}不存在", tableId);

        String physicalName = tlTable.getPhysicalName();

        StringBuilder sql = new StringBuilder();
        sql.append("DELETE FROM ").append(physicalName).append(" WHERE ID=" + rowId);
        jdbcTemplate.execute(sql.toString());

        return true;
    }

    @Override
    public Boolean deleteTable(Long tableId) {
        TLTable tlTable = tlTableDomainService.findById(tableId);
        Assert.notNull(tlTable, "数据表：{}不存在", tableId);
        String physicalName = tlTable.getPhysicalName();
        try {

            String dropTableSql = "drop table " + physicalName;
            jdbcTemplate.execute(dropTableSql);
        } catch (Exception e) {
            log.error("数据表删除异常", e);
        }

        tlTableFileDomainService.deleteByTableId(tableId);
        esUtil.delDocByCol(physicalName, tlTable.getDatabaseId());
        Integer rst = tlTableDomainService.deleteById(tableId);
        return rst > 0 ? true : false;
    }

    @Transactional
    @Override
    public Boolean deleteTableFileData(Long fileId) {
        TLTableFile tlTableFile = tlTableFileDomainService.findById(fileId);
        Assert.notNull(tlTableFile, "数据表文件：{}不存在", fileId);
        String status = tlTableFile.getStatus();
//        Assert.isTrue(FileParseStatusEnum.S30.getCode().equals(status), "数据表文件：{}尚未完成导入", fileId);

        Long tableId = tlTableFile.getTableId();
        TLTable tlTable = tlTableDomainService.findById(tableId);
        Assert.notNull(tlTable, "数据表：{}不存在", tableId);

        String physicalName = tlTable.getPhysicalName();
        StringBuilder sql = new StringBuilder();
        sql.append("DELETE FROM ").append(physicalName).append(" WHERE file_id=" + fileId);
        jdbcTemplate.execute(sql.toString());
        Integer rst = tlTableFileDomainService.deleteById(fileId);
        return rst > 0;
    }

    @Transactional
    @Override
    public Boolean deleteDB(Long databaseId) {
        TLDatabase tlDatabase = tlDatabaseDomainService.findById(databaseId);
        Assert.notNull(tlDatabase, "数据库配置不存在");

        List<TLTable> tableList = tlTableDomainService.list(databaseId);
        for (TLTable tlTable : tableList) {
            try {
                String physicalName = tlTable.getPhysicalName();
                String dropTableSql = "drop table " + physicalName;
                jdbcTemplate.execute(dropTableSql);
            } catch (Exception e) {
                log.error("execute drop table error", e);
            }
        }
        tlTableDomainService.deleteByDatabaseId(databaseId);
        //更新es
        esUtil.delIndex(databaseId);
        //更新配置助手
        databaseConfigClient.updateDbIndex(DB_PREFIX + databaseId);
        return tlDatabaseDomainService.deleteById(databaseId);
    }


}
