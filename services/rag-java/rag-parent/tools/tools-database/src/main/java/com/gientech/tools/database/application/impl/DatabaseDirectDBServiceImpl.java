package com.gientech.tools.database.application.impl;

import cn.hutool.cache.Cache;
import cn.hutool.cache.CacheUtil;
import cn.hutool.core.lang.Assert;
import cn.hutool.db.Db;
import cn.hutool.db.DbUtil;
import cn.hutool.db.Entity;
import cn.hutool.db.PageResult;
import cn.hutool.db.handler.EntityListHandler;
import cn.hutool.db.meta.Column;
import cn.hutool.db.meta.MetaUtil;
import cn.hutool.db.meta.Table;
import cn.hutool.db.sql.SqlExecutor;
import com.alibaba.excel.util.StringUtils;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.tools.database.application.DatabaseDirectDBService;
import com.gientech.tools.database.application.remote.DatabaseConfigClient;
import com.gientech.tools.database.application.remote.DatabaseRemoteService;
import com.gientech.tools.database.domain.entity.TLDatabase;
import com.gientech.tools.database.domain.service.TLDatabaseDomainService;
import com.gientech.tools.database.infrastructure.converter.TLDatabaseConverter;
import com.gientech.ragcommon.index.enmus.DataSourceTypeEnum;
import com.gientech.tools.database.infrastructure.enums.DatabaseTypeEnum;
import com.gientech.tools.database.infrastructure.util.EsUtil;
import com.gientech.tools.database.infrastructure.util.JdbcUtil;
import com.gientech.ragcommon.index.dto.tools.TLDatabaseDTO;
import com.gientech.ragcommon.index.dto.tools.TLTableColumnDto;
import com.gientech.ragcommon.index.dto.tools.TLTableDataDto;
import com.gientech.tools.database.interfaces.dto.TLTableDto;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.SQLException;
import java.util.*;

import static com.gientech.ragcommon.qa.constant.AIConstant.DB_PREFIX;

@Slf4j
@Service
public class DatabaseDirectDBServiceImpl implements DatabaseDirectDBService {

    /** R13-SEC-D3：共享超时执行器（不要每次调用新建线程池，否则泄漏线程）。 */
    private static final java.util.concurrent.Executor NETWORK_TIMEOUT_EXECUTOR =
            java.util.concurrent.Executors.newSingleThreadExecutor(r -> {
                Thread t = new Thread(r, "sql-timeout");
                t.setDaemon(true);
                return t;
            });

    /** 单条结构化查询的秒级上限。 */
    private static final int QUERY_TIMEOUT_SECONDS = 30;
    @Autowired
    private TLDatabaseDomainService tlDatabaseDomainService;

    @Autowired
    private DatabaseRemoteService databaseRemoteService;

    @Autowired
    private DatabaseConfigClient databaseConfigClient;

    @Autowired
    private EsUtil esUtil;

    @Value("${database.pw.enc-key:C7OT8Ty8ghEFRZF1}")
    private String encKey;

    Cache<Long, DataSource> dataSourceCache = CacheUtil.newTimedCache(1000 * 60);

    @Override
    public Boolean testConnect(TLDatabase tlDatabase) {
        tlDatabase.setDatasourceType(DataSourceTypeEnum.DirectDB.getCode());
        String dbType = tlDatabase.getDbType();
        DatabaseTypeEnum databaseTypeEnum = DatabaseTypeEnum.of(dbType);
        if (null == databaseTypeEnum) {
            throw new RuntimeException("数据库类型不匹配");
        }
        Map<String, Object> values = new HashMap<>();
        values.put("host", tlDatabase.getDbHost());
        values.put("port", tlDatabase.getDbPort());
        values.put("database", tlDatabase.getDbDatabase());

        String jdbcUrl = JdbcUtil.jdbcUrlConver(databaseTypeEnum, values);
        String dbUser = tlDatabase.getDbUser();
        String dbPassword = tlDatabase.getDbPassword();
        try {
            DataSource dataSource = JdbcUtil.buildDataSource(jdbcUrl, dbUser, dbPassword);
            Number countNumber = Db.use(dataSource).queryNumber("SELECT 1");
            if (countNumber != null) {
                return true;
            }
        } catch (Exception e) {
            throw new RuntimeException(e);
        }

        return false;
    }

    @Override
    public Long saveDBInfo(TLDatabase tlDatabase) {
        if (Objects.nonNull(tlDatabase) && tlDatabase.getId() == null) {
            preCheck(tlDatabase);
            tlDatabase.setDatasourceType(DataSourceTypeEnum.DirectDB.getCode());
            String dbType = tlDatabase.getDbType();
            DatabaseTypeEnum databaseTypeEnum = DatabaseTypeEnum.of(dbType);
            if (null == databaseTypeEnum) {
                throw new RuntimeException("数据库类型不匹配");
            }
            Map<String, Object> values = new HashMap<>();
            values.put("host", tlDatabase.getDbHost());
            values.put("port", tlDatabase.getDbPort());
            values.put("database", tlDatabase.getDbDatabase());

            String jdbcUrl = JdbcUtil.jdbcUrlConver(databaseTypeEnum, values);
            tlDatabase.setJdbcUrl(jdbcUrl);
        }
        if (Objects.nonNull(tlDatabase) && tlDatabase.getId() != null) {
            TLDatabase originalDatabase = tlDatabaseDomainService.findById(tlDatabase.getId());
            String dbIndex = DB_PREFIX + tlDatabase.getId();
            String originalName = originalDatabase.getName();
            tlDatabaseDomainService.updateById(tlDatabase);
            updateSearchConfig(tlDatabase.getId(), originalName, dbIndex);

        } else {
            tlDatabaseDomainService.save(tlDatabase);
        }
        Long databaseId = tlDatabase.getId();
        databaseRemoteService.batchSyncTableSchema(databaseId);
        return databaseId;
    }

    private void updateSearchConfig(Long databaseId, String originalName, String dbIndex) {
        TLDatabase updatedDatabase = tlDatabaseDomainService.findById(databaseId);
        String updatedName = updatedDatabase.getName();
        if (!originalName.equals(updatedName)){
            //更新配置助手
            databaseConfigClient.renameDbIndex(dbIndex, updatedName, originalName);
        }
    }

    private void preCheck(TLDatabase tlDatabase) {
        if (StringUtils.isEmpty(tlDatabase.getName())) {
            throw new ApplicationException(ErrCodeEnum.NAME_IS_NULL);
        }
        if (StringUtils.isBlank(tlDatabase.getDbType())) {
            throw new ApplicationException(ErrCodeEnum.DB_TYPE_IS_NULL);
        }
        if (StringUtils.isBlank(tlDatabase.getDbHost())) {
            throw new ApplicationException(ErrCodeEnum.DB_HOST_IS_NULL);
        }
        if (Objects.isNull(tlDatabase.getDbPort())) {
            throw new ApplicationException(ErrCodeEnum.DB_PORT_IS_NULL);
        }
        if (StringUtils.isBlank(tlDatabase.getDbDatabase())) {
            throw new ApplicationException(ErrCodeEnum.DB_NAME_IS_NULL);
        }
        if (StringUtils.isBlank(tlDatabase.getDbUser())) {
            throw new ApplicationException(ErrCodeEnum.DB_USER_IS_NULL);
        }
        if (StringUtils.isBlank(tlDatabase.getDbPassword())) {
            throw new ApplicationException(ErrCodeEnum.DB_PASSWORD_IS_NULL);
        }
    }

    @Override
    public TLDatabaseDTO queryDBInfo(Long databaseId) {
        TLDatabase tlDatabase = tlDatabaseDomainService.findById(databaseId);
        Assert.notNull(tlDatabase, "数据库配置不存在");
        TLDatabaseDTO tlDatabaseDTO = TLDatabaseConverter.INSTANCE.convert(tlDatabase);

        Integer highestPermission = tlDatabaseDomainService.getHighestPermission(databaseId);
        tlDatabaseDTO.setPermission(highestPermission);
        return tlDatabaseDTO;
    }

    @Override
    public Long totalOfTables(Long databaseId) {
        DataSource dataSource = buildDataSource(databaseId);
        List<String> tableNames = MetaUtil.getTables(dataSource);
        return Long.valueOf(tableNames.size());
    }

    @Override
    public List<Entity> queryData(Long databaseId, String sql) {
        DataSource dataSource = buildDataSource(databaseId);
        Connection connection = null;
        List<Entity> entityList = new ArrayList<>();
        try {
            connection = dataSource.getConnection();
            // R13-SEC-D3：结构化查询默认只读，并加网络级超时。
            // 原实现只有 SELECT 前缀 + 关键字黑名单 + 强制 LIMIT，没有超时：
            // 一条 `SELECT SLEEP(...)`/大表笛卡尔积就能把请求线程钉死（DoS）。
            try {
                connection.setReadOnly(true);
            } catch (Exception ignore) {
                // 部分驱动/代理不支持只读会话，降级不阻断
            }
            try {
                connection.setNetworkTimeout(NETWORK_TIMEOUT_EXECUTOR, QUERY_TIMEOUT_SECONDS * 1000);
            } catch (Exception ignore) {
            }
            entityList = SqlExecutor.query(connection, sql, new EntityListHandler());
        } catch (SQLException e) {
            throw new RuntimeException("SQL执行出错", e);
        } finally {
            DbUtil.close(connection);
        }

        return entityList;
    }

    @Override
    public List<TLTableDto> pageTableList(Long databaseId) {
        List<TLTableDto> tlTableDtoList = new ArrayList<>();

        DataSource dataSource = buildDataSource(databaseId);
        // 获取数据库权限
        Integer permission = tlDatabaseDomainService.getHighestPermission(databaseId);

        List<String> tableNames = MetaUtil.getTables(dataSource);

        for (String tableName : tableNames) {
            Table tableMeta = MetaUtil.getTableMeta(dataSource, tableName);

            TLTableDto tlTableDto = new TLTableDto();
            String comment = tableMeta.getComment();
            tlTableDto.setDatabaseId(databaseId);
            tlTableDto.setBusinessName(comment);
            tlTableDto.setPhysicalName(tableName);
            tlTableDto.setDescription(comment);
            tlTableDto.setColumnCount(tableMeta.getColumns().size());

            try {
                Number countNumber = Db.use(dataSource).queryNumber("SELECT COUNT(1) FROM " + tableName);
                long rowCount = countNumber != null ? countNumber.longValue() : 0L;
                tlTableDto.setRowCount(rowCount);
            } catch (SQLException e) {
                log.error("查询数据表数据量发生错误", e);
                throw new RuntimeException(e);
            }
            tlTableDto.setPermission(permission);
            tlTableDtoList.add(tlTableDto);
        }

        log.debug("TableList:" + tableNames);
        return tlTableDtoList;
    }

    @Override
    public TLTableDto queryTableMeta(Long databaseId, String tableName) {
        DataSource dataSource = buildDataSource(databaseId);

        Table tableMeta = MetaUtil.getTableMeta(dataSource, tableName);

        TLTableDto tlTableDto = new TLTableDto();
        String comment = tableMeta.getComment();
        tlTableDto.setDatabaseId(databaseId);
        tlTableDto.setBusinessName(comment);
        tlTableDto.setPhysicalName(tableName);
        tlTableDto.setDescription(comment);

        Collection<Column> columns = tableMeta.getColumns();
        Assert.isFalse(tableMeta.getComment() == null && columns.size() == 0, "数据表:{}疑似不存在", tableName);

        tlTableDto.setColumnCount(columns.size());
        Map<String, List<String>> sampleValueMap = new HashMap<>();
        try {
            Entity entityWhere = new Entity();
            entityWhere.setTableName(tableName);
            PageResult<Entity> pageTableData = Db.use(dataSource).page(entityWhere, 1, 3);
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


        List<TLTableColumnDto> tlTableColumnDtos = new ArrayList<>();
        for (Column column : columns) {
            String name = column.getName();
            TLTableColumnDto tlTableColumnDto = new TLTableColumnDto();
            tlTableColumnDto.setPhysicalName(name);
            tlTableColumnDto.setBusinessName(column.getComment());
            tlTableColumnDto.setDataType(column.getTypeName());
            tlTableColumnDto.setSampleValues(sampleValueMap.getOrDefault(name, new ArrayList<>()));

            tlTableColumnDtos.add(tlTableColumnDto);
        }
        tlTableDto.setColumns(tlTableColumnDtos);

        return tlTableDto;
    }

    @Override
    public TLTableDataDto pageTableData(Long databaseId, String tableName, Long pageNo, Long pageSize) {
        pageNo = Objects.isNull(pageNo) ? 1 : pageNo;
        pageSize = Objects.isNull(pageSize) ? 10 : pageSize;

        DataSource dataSource = buildDataSource(databaseId);
        TLTableDataDto tlTableDataDto = new TLTableDataDto();
        tlTableDataDto.setTableName(tableName);

        TLTableDto tlTableDto = queryTableMeta(databaseId, tableName);
        tlTableDataDto.setColumns(tlTableDto.getColumns());
        try {
            Entity entityWhere = new Entity();
            entityWhere.setTableName(tableName);
            PageResult<Entity> pageTableData = Db.use(dataSource).page(entityWhere, pageNo.intValue() - 1, pageSize.intValue());

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
    public Boolean deleteDB(Long databaseId) {
        TLDatabase tlDatabase = tlDatabaseDomainService.findById(databaseId);
        Assert.notNull(tlDatabase, "数据库配置不存在");
        Long id = tlDatabase.getId();
        //更新es
        esUtil.delIndex(databaseId);
        //更新配置助手
        databaseConfigClient.updateDbIndex(DB_PREFIX + databaseId);
        return tlDatabaseDomainService.deleteById(id);
    }


    /**
     * 根据数据库编号，创建数据库连接的datasource
     *
     * @param databaseId
     * @return
     */
    private DataSource buildDataSource(Long databaseId) {
        TLDatabase tlDatabase = tlDatabaseDomainService.findByIdOfDec(databaseId);
        Assert.notNull(tlDatabase, "数据库配置不存在");

        String jdbcUrl = tlDatabase.getJdbcUrl();
        String dbUser = tlDatabase.getDbUser();
        String dbPassword = tlDatabase.getDbPassword();

        DataSource dataSource = dataSourceCache.get(databaseId);
        if (dataSource == null) {
            dataSource = JdbcUtil.buildDataSource(jdbcUrl, dbUser, dbPassword);
            dataSourceCache.put(databaseId, dataSource);
        }

        return dataSource;
    }
}
