package com.gientech.tools.database.application.remote;

import cn.hutool.core.lang.Assert;
import cn.hutool.json.JSONArray;
import cn.hutool.json.JSONConfig;
import cn.hutool.json.JSONObject;
import cn.hutool.json.JSONUtil;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.index.dto.ModelSimpDTO;
import com.gientech.ragcommon.index.response.PyEsResponse;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.tools.database.application.DatabaseDataTableService;
import com.gientech.tools.database.application.DatabaseDirectDBService;
import com.gientech.tools.database.domain.entity.TLDatabase;
import com.gientech.tools.database.domain.service.TLDatabaseDomainService;
import com.gientech.tools.database.domain.service.TLTableDomainService;
import com.gientech.ragcommon.index.enmus.DataSourceTypeEnum;
import com.gientech.tools.database.infrastructure.util.JsonNamingConvertUtil;
import com.gientech.tools.database.interfaces.dto.TLTableDto;
import com.gientech.tools.database.interfaces.request.EsDelRequest;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.context.config.annotation.RefreshScope;
import org.springframework.http.*;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.List;

import static com.gientech.ragcommon.qa.constant.AIConstant.DB_PREFIX;
import static com.gientech.ragcommon.qa.constant.AIConstant.DEFAULT_DATABASE_NAME;

/**
 * 与算法交互相关逻辑
 */
@Slf4j
@RefreshScope
@Service
public class DatabaseRemoteService {
    /**
     * 数据库接入：同步数据表结构到es
     * 调用接口和faq保存一致，使用同种结构向es中保存数据
     */
    @Value("${remote.faq-sava-es.url}")
    private String tlDatabseSyncTableSchemaUrl;

    /**
     * 数据库接入：生成数据表描述
     */
    @Value("${remote.tl-database-table-description.url}")
    private String tlDatabseTableDescriptionUrl;

    @Autowired
    private TLDatabaseDomainService tlDatabaseDomainService;

    @Autowired
    private TLTableDomainService tlTableDomainService;

    @Autowired
    private DatabaseDirectDBService databaseDirectDBService;

    @Autowired
    private DatabaseDataTableService databaseDataTableService;

    @Autowired
    private RestTemplate restTemplate;

    @Autowired
    private EsClient esClient;


    @Async
    public void batchSyncTableSchema(Long databaseId) {
        TLDatabase tlDatabase = tlDatabaseDomainService.findById(databaseId);
        Assert.notNull(tlDatabase, "数据库配置不存在");

        // 先删除数据库中所有的表
        deleteEsDatabase(databaseId);

        String datasourceType = tlDatabase.getDatasourceType();
        if (DataSourceTypeEnum.of(datasourceType).equals(DataSourceTypeEnum.DataTable)) {
            Long totalOfTables = databaseDataTableService.totalOfTables(databaseId);

            long pageSize = 50;
            long pages = totalOfTables / pageSize + 1;

            for (int i = 1; i <= pages; i++) {
                Page<TLTableDto> tlTableDtoPage = databaseDataTableService.pageTableList(databaseId, Long.valueOf(i), pageSize);
                List<TLTableDto> records = tlTableDtoPage.getRecords();
                for (TLTableDto tlTableDto : records) {
                    String tableName = tlTableDto.getPhysicalName();
                    syncTableSchema(databaseId, tableName);
                }
            }

        } else if (DataSourceTypeEnum.of(datasourceType).equals(DataSourceTypeEnum.DirectDB)) {
            List<TLTableDto> tlTableDtoList = databaseDirectDBService.pageTableList(databaseId);
            for (TLTableDto tlTableDto : tlTableDtoList) {
                String tableName = tlTableDto.getPhysicalName();
                syncTableSchema(databaseId, tableName);
            }
        }
    }

    /**
     * 删除es中数据库的所有表
     */
    public void deleteEsDatabase(Long databaseId) {
        EsDelRequest delRequest = new EsDelRequest();
        delRequest.setIndexName(DB_PREFIX + databaseId);
        try {
            PyEsResponse<Object> pyEsResponse = esClient.delIndex(delRequest);
            if (pyEsResponse.getCode().equals(HttpStatus.OK.value())) {
                log.info("db{} es index delete ok", databaseId);
            } else {
                log.error("db{} es index delete error", databaseId);
            }
        } catch (Exception e) {
            log.error(e.getMessage(), e);
        }
    }

    /**
     * 同步数据表结构到es
     *
     * @param databaseId
     * @param tableName
     * @return
     */
    public Boolean syncTableSchema(Long databaseId, String tableName) {
        log.info("同步数据表结构-开始，databaseId：{}，tableName：{}", databaseId, tableName);
        JSONConfig jsonConfig = new JSONConfig();
        jsonConfig.setIgnoreNullValue(false);
        JSONObject param = new JSONObject(jsonConfig);
        param.set("index_name", "db" + databaseId);
        param.set("type", "database");
        param.set("databaseId", databaseId);
        param.set("tableName", tableName);

        JSONArray jsonArray = new JSONArray();

        TLTableDto tlTableDto = getTLTableDto(databaseId, tableName);
        JSONObject tlTableDtoJson = new JSONObject(tlTableDto, false);
        JSONObject jsonObject = JsonNamingConvertUtil.convertObject(tlTableDtoJson);
        jsonArray.add(jsonObject);

        param.set("document_list", jsonArray);

        String remoteRst = tlDatabseSyncTableSchema(JSONUtil.toJsonStr(param));
        JSONObject rstJsonObj = JSONUtil.toBean(remoteRst, JSONObject.class);
        Integer code = rstJsonObj.getInt("code");
        if (code == null || code != 200) {
            String errorLog = "同步数据表结构发生错误：" + remoteRst;
            log.error(errorLog);
            throw new RuntimeException(errorLog);
        }
        log.info("同步数据表结构-结束，databaseId：{}，tableName：{}", databaseId, tableName);
        return true;
    }

    /**
     * 生成数据表描述（仅支持数据表）
     *
     * @param tableId
     * @return
     */
    public String genTableDescription(Long tableId, ModelSimpDTO modelSimpDTO) {
        TLTableDto tlTableDto = databaseDataTableService.queryTableMeta(tableId);
        com.alibaba.fastjson2.JSONObject param = com.alibaba.fastjson2.JSONObject.from(tlTableDto);
        param.put("model_info", modelSimpDTO);
        String jsonStr = param.toJSONString();

        String remoteRst = tlDatabseGenTableDescription(jsonStr);
        com.alibaba.fastjson2.JSONObject rstJsonObj = com.alibaba.fastjson2.JSONObject.parseObject(remoteRst);
        Boolean success = rstJsonObj.getBoolean("success");
        if (success) {
            String description = rstJsonObj.getString("table_description");
            return description;
        } else {
            String errorLog = "生成表描述发生错误：" + remoteRst;
            log.error(errorLog);
            throw new RuntimeException(errorLog);
        }
    }

    /**
     * 生成并更新数据表描述（仅支持数据表）
     *
     * @param databaseId
     * @param tableName
     * @return
     */
    public Boolean genUpdateTableDescription(Long databaseId, String tableName, ModelSimpDTO modelSimpDTO) {
        TLTableDto tlTableDto = databaseDataTableService.queryTableMetaByTableName(databaseId, tableName);
        com.alibaba.fastjson2.JSONObject param = com.alibaba.fastjson2.JSONObject.from(tlTableDto);
        param.put("model_info", modelSimpDTO);
        String jsonStr = param.toJSONString();

        String remoteRst = tlDatabseGenTableDescription(jsonStr);
        com.alibaba.fastjson2.JSONObject rstJsonObj = com.alibaba.fastjson2.JSONObject.parseObject(remoteRst);
        Boolean success = rstJsonObj.getBoolean("success");
        if (success) {
            String description = rstJsonObj.getString("table_description");
            databaseDataTableService.updateTableDescription(databaseId, tableName, description);
        } else {
            String errorLog = "生成表描述发生错误：" + remoteRst;
            databaseDataTableService.updateGenDescErrMsg(tlTableDto.getId(), errorLog);
            log.error(errorLog);
            throw new RuntimeException(errorLog);
        }
        return true;
    }

    /**
     * 获取字段详情
     *
     * @param databaseId
     * @param tableName
     * @return
     */
    private TLTableDto getTLTableDto(Long databaseId, String tableName) {
        TLDatabase tlDatabase = tlDatabaseDomainService.findById(databaseId);
        Assert.notNull(tlDatabase, "数据库配置不存在");

        String datasourceType = tlDatabase.getDatasourceType();
        TLTableDto tlTableDto = null;
        if (DataSourceTypeEnum.of(datasourceType).equals(DataSourceTypeEnum.DataTable)) {
            tlTableDto = databaseDataTableService.queryTableMetaByTableName(databaseId, tableName);
            tlTableDto.setDatabaseName(DEFAULT_DATABASE_NAME);

        } else if (DataSourceTypeEnum.of(datasourceType).equals(DataSourceTypeEnum.DirectDB)) {
            tlTableDto = databaseDirectDBService.queryTableMeta(databaseId, tableName);
            tlTableDto.setDatabaseName(tlDatabase.getDbDatabase());
        }
        tlTableDto.setDatabaseDescription(tlDatabase.getDescription());

        return tlTableDto;
    }

    public String tlDatabseSyncTableSchema(String requestPara) {
        return doExchange(requestPara, tlDatabseSyncTableSchemaUrl, HttpMethod.POST).getBody();
    }

    public String tlDatabseGenTableDescription(String requestPara) {
        return doExchange(requestPara, tlDatabseTableDescriptionUrl, HttpMethod.POST).getBody();
    }


    private ResponseEntity<String> doExchange(String param, String url, HttpMethod httpMethod) {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        HttpEntity<Object> requestEntity = new HttpEntity<>(param, headers);
        log.info("远程url:{},请求方式:{},请求参数:{}", url, httpMethod.name(), param);
        ResponseEntity<String> response = restTemplate.exchange(url, httpMethod, requestEntity, String.class);
        log.info("远程url:{},响应结果:{}", url, JSONUtil.toJsonStr(response.getBody()));
        HttpStatusCode httpStatusCode = response.getStatusCode();
        if (200 != httpStatusCode.value()) {
            throw new ApplicationException(ErrCodeEnum.FILE_PARSE_ERROR);
        }
        return response;
    }
}
