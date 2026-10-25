package com.gientech.ragindexservice.application.service.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.collection.CollUtil;
import cn.hutool.core.date.DateUtil;
import cn.hutool.core.io.IoUtil;
import cn.hutool.core.io.file.FileNameUtil;
import cn.hutool.core.lang.Assert;
import cn.hutool.core.lang.UUID;
import cn.hutool.core.util.StrUtil;
import cn.hutool.db.Entity;
import com.alibaba.fastjson2.JSON;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.auth.dto.PrivilegeDTO;
import com.gientech.ragcommon.auth.enums.PrivilegeTypeEnums;
import com.gientech.ragcommon.auth.enums.RoleTypeEnums;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.index.dto.ModelSimpDTO;
import com.gientech.ragcommon.index.enmus.PermissionEnums;
import com.gientech.ragcommon.index.request.QueryDataReq;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.ragindexservice.application.remote.PrivilegeClient;
import com.gientech.ragindexservice.application.remote.UserClient;
import com.gientech.ragindexservice.application.service.ModelInfoAppService;
import com.gientech.ragindexservice.application.service.TLDatabaseAppService;
import com.gientech.ragindexservice.infrastructure.MultipartFileUtils;
import com.gientech.start.redisson.utils.RedissonUtils;
import com.gientech.start.storage.exception.FileStorageException;
import com.gientech.start.storage.model.FileInfo;
import com.gientech.start.storage.properties.StorageProperties;
import com.gientech.start.storage.utils.FileStorageUtils;
import com.gientech.tools.database.application.DatabaseDataTableService;
import com.gientech.tools.database.application.DatabaseDirectDBService;
import com.gientech.tools.database.application.remote.DatabaseRemoteService;
import com.gientech.tools.database.domain.entity.TLDatabase;
import com.gientech.tools.database.domain.entity.TLTable;
import com.gientech.tools.database.domain.entity.TLTableFile;
import com.gientech.tools.database.domain.service.TLDatabaseDomainService;
import com.gientech.tools.database.domain.service.TLTableDomainService;
import com.gientech.tools.database.domain.service.TLTableFileDomainService;
import com.gientech.tools.database.infrastructure.calback.ParseFileCallback;
import com.gientech.ragcommon.index.enmus.DataSourceTypeEnum;
import com.gientech.tools.database.infrastructure.enums.FileParseStatusEnum;
import com.gientech.tools.database.infrastructure.enums.GenDescStatusEnum;
import com.gientech.tools.database.infrastructure.util.DataTableFileTypeChecker;
import com.gientech.tools.database.interfaces.dto.ResultDto;
import com.gientech.ragcommon.index.dto.tools.TLDatabaseDTO;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.function.Function;
import java.util.stream.Collectors;

@Slf4j
@Service
public class TLDatabaseAppServiceImpl implements TLDatabaseAppService {

    @Autowired
    private TLDatabaseDomainService tlDatabaseDomainService;

    @Autowired
    private TLTableDomainService tlTableDomainService;

    @Autowired
    private TLTableFileDomainService tlTableFileDomainService;

    @Autowired
    private DatabaseDataTableService databaseDataTableService;

    @Autowired
    private DatabaseDirectDBService databaseDirectDBService;

    @Autowired
    private DatabaseRemoteService databaseRemoteService;

    @Autowired
    private FileStorageUtils fileStorageUtils;

    @Autowired
    private UserClient userClient;

    @Autowired
    private PrivilegeClient privilegeClient;

    @Autowired
    private JdbcTemplate jdbcTemplate;

    @Autowired
    private StorageProperties storageProperties;

    @Autowired
    private RedissonUtils redissonUtils;

    @Value(("${remote.database-table-description.model}"))
    private String databaseTableDescriptionModelName;

    private final String STORAGE_FOLDER = "database/";
    @Autowired
    private ModelInfoAppService modelInfoAppService;

    @Override
    public Page<TLDatabaseDTO> pageDBList(Long pageNo, Long pageSize, String fuzzyWord, String userName, Boolean includingCreator) {
        pageNo = Objects.isNull(pageNo) ? 1 : pageNo;
        pageSize = Objects.isNull(pageSize) ? 10 : pageSize;

        Page<TLDatabaseDTO> rst = new Page<>(pageNo, pageSize);
        Page<TLDatabase> page = tlDatabaseDomainService.page(DataSourceTypeEnum.All, pageNo, pageSize, fuzzyWord, userName, includingCreator);
        BeanUtil.copyProperties(page, rst);

        List<TLDatabaseDTO> tlDatabaseDTOS = BeanUtil.copyToList(page.getRecords(), TLDatabaseDTO.class);
        rst.setRecords(tlDatabaseDTOS);

        return rst;
    }

    @Override
    public Page<TLDatabaseDTO> shareDBList(Long pageNo, Long pageSize, String fuzzyWord) {
        pageNo = Objects.isNull(pageNo) ? 1 : pageNo;
        pageSize = Objects.isNull(pageSize) ? 10 : pageSize;

        if (RoleTypeEnums.SUPER_ADMIN.getCode().equals(userClient.getUserType())) {
            Page<TLDatabaseDTO> page = pageDBList(pageNo, pageSize, fuzzyWord, UserContext.getUser().getUserName(), Boolean.FALSE);
            page.getRecords().forEach(tlDatabaseDTO -> tlDatabaseDTO.setPermission(PermissionEnums.ALL.getCode()));
            return page;
        }
        List<PrivilegeDTO> privilegeDTOList = privilegeClient.getAllPermission(PrivilegeTypeEnums.DATABASE.getCode(), null);
        if (CollUtil.isEmpty(privilegeDTOList)) {
            return new Page<>();
        }

        Map<Long, PrivilegeDTO> permissionMap = privilegeDTOList.stream().collect(Collectors.toMap(PrivilegeDTO::getTargetId, Function.identity(), (v1, v2) -> v1));

        Page<TLDatabase> tlDatabasePage = tlDatabaseDomainService.pageByTargetIds(new ArrayList<>(permissionMap.keySet()), pageNo, pageSize, fuzzyWord, Boolean.FALSE);
        Page<TLDatabaseDTO> result = new Page<>();
        BeanUtil.copyProperties(tlDatabasePage, result);

        List<TLDatabaseDTO> tlDatabaseDTOS = BeanUtil.copyToList(tlDatabasePage.getRecords(), TLDatabaseDTO.class);
        for (TLDatabaseDTO tlDatabaseDto : tlDatabaseDTOS) {
            PrivilegeDTO privilegeDTO = permissionMap.get(tlDatabaseDto.getId());
            if (Objects.nonNull(privilegeDTO)) {
                tlDatabaseDto.setPermission(privilegeDTO.getPermission());
            }
        }

        result.setRecords(tlDatabaseDTOS);
        return result;
    }

    @Override
    public Set<TLDatabaseDTO> searchAllDB(String fuzzyWord) {
        Set<TLDatabaseDTO> result = new HashSet<>();
        Page<TLDatabaseDTO> shareDBs = shareDBList(1L, 9999L, fuzzyWord);
        Page<TLDatabaseDTO> currentUserDBs = pageDBList(1L, 9999L, fuzzyWord, UserContext.getUser().getUserName(), Boolean.TRUE);
        result.addAll(shareDBs.getRecords());
        result.addAll(currentUserDBs.getRecords());
        return result;
    }

    @Override
    public String queryDatabaseCreator(Long databaseId) {
        TLDatabase tlDatabase = tlDatabaseDomainService.findById(databaseId);
        return Objects.isNull(tlDatabase) ? null : tlDatabase.getCreateBy();
    }

    /** R13：单次结构化查询的最大返回行数（防大表全扫） */
    private static final int MAX_QUERY_ROWS = 500;

    /**
     * R13-SEC-D1：数据库对象级授权。
     * 允许：超级管理员、库创建人、在 user/dept/group_privilege 中具备该库读权限（bizType=12）。
     */
    private void assertDatabaseReadable(TLDatabase tlDatabase) {
        Integer userType = userClient.getUserType();
        if (com.gientech.ragcommon.auth.enums.RoleTypeEnums.SUPER_ADMIN.getCode().equals(userType)) {
            return;
        }
        String currentUser = com.gientech.ragcommon.context.user.UserContext.getUser() == null
                ? null : com.gientech.ragcommon.context.user.UserContext.getUser().getUserName();
        if (currentUser != null && currentUser.equals(tlDatabase.getCreateBy())) {
            return;
        }
        java.util.Map<Long, com.gientech.ragcommon.auth.dto.PrivilegeDTO> permissionMap =
                privilegeClient.getPermission(com.gientech.ragcommon.auth.enums.PrivilegeTypeEnums.DATABASE.getCode(), null);
        com.gientech.ragcommon.auth.dto.PrivilegeDTO dto =
                permissionMap == null ? null : permissionMap.get(tlDatabase.getId());
        int permission = dto == null || dto.getPermission() == null ? 0 : dto.getPermission();
        if (permission < 1) {
            log.warn("R13-SEC-D1 deny database query: databaseId={} user={}", tlDatabase.getId(), currentUser);
            throw new com.gientech.ragcommon.infrastructure.exception.ApplicationException(
                    com.gientech.ragcommon.global.ErrCodeEnum.INSUFFICIENT_PERMISSIONS);
        }
    }

    @Override
    public List<Entity> queryData(QueryDataReq executeSqlReq) {
        Long databaseId = executeSqlReq.getDatabaseId();
        String sql = executeSqlReq.getSql();

        Assert.notBlank(sql, "SQL语句为空");

        Assert.isTrue(sql.trim().toUpperCase().startsWith("SELECT") || sql.trim().toUpperCase().startsWith("WITH"),
                "仅支持SQL查询语句");

        Assert.isFalse(sql.contains(";"), "SQL语句中不允许出现终止符;");

        TLDatabase tlDatabase = tlDatabaseDomainService.findById(databaseId);

        Assert.notNull(tlDatabase, "数据库配置不存在");

        // R13-SEC-D1：结构化查询的对象级授权。原来只要登录就能对任意 databaseId 执行 SQL。
        assertDatabaseReadable(tlDatabase);

        // R13-SEC-D2：SELECT 前缀校验可被 `SELECT ... INTO OUTFILE`、`SELECT SLEEP(1000)`、
        // CTE 内 DML 等绕过，这里加危险关键字黑名单 + 强制行数上限。
        String normalized = sql.replaceAll("\\s+", " ").toUpperCase();
        String[] banned = {"INTO OUTFILE", "INTO DUMPFILE", "LOAD_FILE", "SLEEP(", "BENCHMARK(",
                "INSERT ", "UPDATE ", "DELETE ", "DROP ", "ALTER ", "TRUNCATE ", "CREATE ",
                "GRANT ", "REVOKE ", "CALL ", "LOAD DATA", "SET GLOBAL", "SHUTDOWN"};
        for (String kw : banned) {
            Assert.isFalse(normalized.contains(kw), "SQL语句包含不允许的关键字：" + kw.trim());
        }
        if (!normalized.matches(".*\\bLIMIT\\b.*")) {
            sql = sql + " LIMIT " + MAX_QUERY_ROWS;
        }

        List<Entity> entityList = new ArrayList<>();

        String datasourceType = tlDatabase.getDatasourceType();

        if (Objects.equals(DataSourceTypeEnum.of(datasourceType), DataSourceTypeEnum.DataTable)) {
            entityList = databaseDataTableService.queryData(databaseId, sql);
        } else if (Objects.equals(DataSourceTypeEnum.of(datasourceType), DataSourceTypeEnum.DirectDB)) {
            entityList = databaseDirectDBService.queryData(databaseId, sql);
        }

        saveSqlData(executeSqlReq, entityList);

        return entityList;
    }


    private void saveSqlData(QueryDataReq executeSqlReq, List<Entity> entityList) {
        QueryDataReq.SqlQueryInfo sqlQueryInfo = executeSqlReq.getSqlQueryInfo();
        if (Objects.nonNull(sqlQueryInfo)) {
            log.info("start converting sql data to json file...");
            //JSONArray formattedJson = entityListToJSONArray(entityList);

            try (InputStream inputStream = json2InputStream(JSON.toJSONString(entityList))) {
                MultipartFile multipartFile = MultipartFileUtils.convertToMultipartFile(inputStream, sqlQueryInfo.getDialogueId() + "-" + UUID.randomUUID().toString(true) + ".json");
                log.info("convert json file to multipart file...");
                FileInfo fileInfo = fileStorageUtils.putObject("retrieve-sql-data/", multipartFile, storageProperties.getDefaultPlatform());
                log.info("json file saved.");
                String filePath = fileInfo.getFilePath();
                log.info("sql data filePath:{}", filePath);
                redissonUtils.set(sqlQueryInfo.getSqlQueryKey(), filePath);
                log.info("set redis key: {}", sqlQueryInfo.getSqlQueryKey());
            } catch (IOException | FileStorageException e) {
                log.error("save sql data failed!", e);
                throw new RuntimeException(e);
            }
        }
    }

    private InputStream json2InputStream(String json) {
        byte[] bytes = json.getBytes(StandardCharsets.UTF_8);
        return new ByteArrayInputStream(bytes);
    }

    @Override
    public Long uploadFile(Long databaseId, Long tableId, MultipartFile multipartFile) {
        TLTableFile tlTableFile = new TLTableFile();


        String fileName = multipartFile.getOriginalFilename();
        String extName = Objects.requireNonNull(FileNameUtil.extName(fileName)).toLowerCase();

        if (!extName.equals("xls") && !extName.equals("xlsx") && !extName.equals("csv")) {
            throw new RuntimeException("文件格式不支持，支持EXCEL、CSV");
        }
        checkDuplication(tableId, fileName);

        try {
            String realExtType = DataTableFileTypeChecker.detectExcelType(multipartFile.getInputStream());
            if (!realExtType.equals("xls") && !realExtType.equals("xlsx") && !realExtType.equals("csv")) {
                throw new RuntimeException("文件格式错误，文件或许被破坏");
            }
        } catch (Exception e) {
            throw new RuntimeException("读取文件流失败", e);
        }

        ResultDto<Boolean> resultDto = databaseDataTableService.validateTableFile(databaseId, tableId, multipartFile);
        Assert.isTrue(resultDto.getData(), resultDto.getMessage());

        Map<String, Object> extraMap = resultDto.getExtra();
        Integer columnCount = Integer.valueOf(extraMap.get("columnCount").toString());
        Long rowCount = Long.valueOf(extraMap.get("rowCount").toString());
        tlTableFile.setColumnCount(columnCount);
        tlTableFile.setRowCount(rowCount);

        tlTableFile.setTableId(tableId);

        try {
            String folder = STORAGE_FOLDER + DateUtil.thisYear() + "/" + DateUtil.thisMonth() + "/";
            String objectName = UUID.fastUUID() + "." + extName;
            FileInfo fileInfo = fileStorageUtils.putObject(folder, multipartFile, objectName, null);

            BeanUtil.copyProperties(fileInfo, tlTableFile);
            tlTableFile.setOriginalFilename(fileName);
            tlTableFile.setFolderPath(folder);
        } catch (FileStorageException e) {
            throw new RuntimeException("对象存储上传错误", e);
        }
        tlTableFile.setDatabaseId(databaseId);
        tlTableFile.setStatus(FileParseStatusEnum.S10.getCode());
        tlTableFileDomainService.save(tlTableFile);

        return tlTableFile.getId();
    }

    private void checkDuplication(Long tableId, String fileName) {
        //仅查询是点击确认导入之后的文件
        List<TLTableFile> tlTableFiles = tlTableFileDomainService.listUploadedByTableId(tableId);
        Set<String> fileNames = new HashSet<>();
        for (TLTableFile tlTable : tlTableFiles) {
            fileNames.add(tlTable.getOriginalFilename());
        }
        if (!fileNames.add(fileName)) {
            log.error("追加文件与已有文件名称重复");
            throw new ApplicationException(ErrCodeEnum.APPEND_DATA_TABLE_FILE_NAME_EXISTS);
        }
    }

    @Override
    public Boolean cancelUploadFile(List<Long> fileIds) {
        for (Long fileId : fileIds) {
            tlTableFileDomainService.deleteById(fileId);
        }
        return true;
    }


    @Override
    public void parseFiles(List<Long> fileIds, Map<Long, String> tableDescriptionMap, Boolean isGenDescription) {
        for (Long fileId : fileIds) {
            TLTableFile tlTableFile = tlTableFileDomainService.findById(fileId);

            if (tlTableFile == null) {
                log.error("待解析的文件：" + fileId + "，不存在！");
                continue;
            }

            if (!tlTableFile.getStatus().equals(FileParseStatusEnum.S10.getCode())) {
                log.error("文件：" + fileId + "，可能已被解析或解析报错！");
                continue;
            }

            Long databaseId = tlTableFile.getDatabaseId();
            String originalFilename = tlTableFile.getOriginalFilename();
            String prefixName = FileNameUtil.getPrefix(originalFilename);

            TLTable tlTable = new TLTable();
            tlTable.setDatabaseId(databaseId);
            tlTable.setBusinessName(prefixName);
            tlTable.setIsGenDesc(isGenDescription);
            tlTableDomainService.save(tlTable);

            Long tableId = tlTable.getId();
            tlTableFile.setTableId(tableId);
            tlTableFileDomainService.updateById(tlTableFile);
            if (isGenDescription) {
                databaseDataTableService.updateGenDescStatus(tableId, GenDescStatusEnum.GENERATING);
            }
            // 解析文件，数据入库
            String filePath = tlTableFile.getFilePath();
            InputStream inputStream = null;
            try {
                inputStream = fileStorageUtils.getInputStream(filePath);

                // 文件解析完成后的异步回调
                ParseFileCallback parseFileCallback = new ParseFileCallback() {
                    @Override
                    public void onComplete(TLTable rstTlTable) {
                        String physicalName = rstTlTable.getPhysicalName();

                        // 自定义表描述
                        String tableDescription = tableDescriptionMap.get(fileId);
                        boolean useCustomDescription = false;
                        if (tableDescription != null && !tableDescription.isEmpty()) {
                            databaseDataTableService.updateTableDescription(databaseId, physicalName, tableDescription);
                            useCustomDescription = true;
                        }

                        // 是否自动生成表描述
                        if (!useCustomDescription && isGenDescription) {
                            try {
                                ModelSimpDTO simpByModeName = modelInfoAppService.getSimpByModeName(databaseTableDescriptionModelName);
                                if (Objects.isNull(simpByModeName)) {
                                    throw new ApplicationException(ErrCodeEnum.MODEL_NOT_AVAILABLE.getErrCode(), databaseTableDescriptionModelName);
                                }
                                databaseRemoteService.genUpdateTableDescription(databaseId, physicalName, simpByModeName);
                            } catch (Exception e) {
                                log.error("generating table description error", e);
                                databaseDataTableService.updateGenDescErrMsg(databaseId, physicalName, e.getMessage());
                            }
                        }

                        // 同步表结构
                        databaseRemoteService.syncTableSchema(databaseId, physicalName);
                    }
                };

                databaseDataTableService.uploadParseFile(tlTableFile, inputStream, parseFileCallback);
            } catch (Exception e) {
                String errorMsg = StrUtil.sub(e.getMessage(), 0, 900);
                tlTableFile.setStatus(FileParseStatusEnum.S00.getCode());
                tlTableFile.setErrorMsg(errorMsg);
                tlTableFileDomainService.updateById(tlTableFile);
                log.error("文件解析出错", e);
            }

        }

    }


    @Override
    public void parseAppendFiles(List<Long> fileIds, Long tableId) {

        for (Long fileId : fileIds) {
            TLTableFile tlTableFile = tlTableFileDomainService.findById(fileId);

            String filePath = tlTableFile.getFilePath();
            InputStream inputStream = null;
            try {
                inputStream = fileStorageUtils.getInputStream(filePath);
                databaseDataTableService.appendParseFile(tlTableFile, inputStream);
            } catch (Exception e) {
                String errorMsg = StrUtil.sub(e.getMessage(), 0, 900);
                tlTableFile.setStatus(FileParseStatusEnum.S00.getCode());
                tlTableFile.setErrorMsg(errorMsg);
                tlTableFileDomainService.updateById(tlTableFile);
            } finally {
                IoUtil.close(inputStream);
            }
        }
    }

    @Override
    public void reParseFile(Long fileId) {
        TLTableFile tlTableFile = tlTableFileDomainService.findById(fileId);
        tlTableFile.setUseTime(null);
        tlTableFile.setStatus(FileParseStatusEnum.S10.getCode());
        tlTableFile.setErrorMsg(null);
        tlTableFileDomainService.updateById(tlTableFile);
        InputStream inputStream = null;
        try {
            Long tableId = tlTableFile.getTableId();
            TLTable tlTable = tlTableDomainService.findById(tableId);
            Assert.notNull(tlTable, "数据表：{}不存在", tableId);

            String physicalName = tlTable.getPhysicalName();
            StringBuilder sql = new StringBuilder();
            sql.append("DELETE FROM ").append(physicalName).append(" WHERE file_id=" + fileId);
            jdbcTemplate.execute(sql.toString());

            String filePath = tlTableFile.getFilePath();

            inputStream = fileStorageUtils.getInputStream(filePath);
            databaseDataTableService.appendParseFile(tlTableFile, inputStream);
        } catch (Exception e) {
            String errorMsg = StrUtil.sub(e.getMessage(), 0, 900);
            tlTableFile.setStatus(FileParseStatusEnum.S00.getCode());
            tlTableFile.setErrorMsg(errorMsg);
            tlTableFileDomainService.updateById(tlTableFile);
        } finally {
            IoUtil.close(inputStream);
        }
    }

    @Override
    public TLDatabaseDTO findById(Long databaseId) {
        TLDatabase database = tlDatabaseDomainService.findById(databaseId);
        if (Objects.nonNull(database)) {
            return BeanUtil.copyProperties(database, TLDatabaseDTO.class);
        }
        return null;

    }
}
