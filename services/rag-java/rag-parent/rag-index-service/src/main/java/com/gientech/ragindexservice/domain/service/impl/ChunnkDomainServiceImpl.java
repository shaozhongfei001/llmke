package com.gientech.ragindexservice.domain.service.impl;

import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.plugins.pagination.PageDTO;
import com.gientech.ragcommon.auth.enums.BizTypeEnums;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.index.enmus.FileFieldEnums;
import com.gientech.ragcommon.index.request.FaqQueryReq;
import com.gientech.ragcommon.index.request.PyLabelReq;
import com.gientech.ragcommon.index.response.PyEsResponse;
import com.gientech.ragcommon.index.response.PyMilvusResponse;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.ragcommon.infrastructure.exception.DomainException;
import com.gientech.ragindexservice.application.remote.PyEsClient;
import com.gientech.ragindexservice.application.remote.PyMilvusClient;
import com.gientech.ragindexservice.domain.entity.FaqEsInfo;
import com.gientech.ragindexservice.domain.entity.FaqEsResponse;
import com.gientech.ragindexservice.domain.entity.FaqInfo;
import com.gientech.ragindexservice.domain.service.ChunnkDomainService;
import com.gientech.ragindexservice.infrastructure.RemoteFileUtils;
import com.gientech.ragindexservice.infrastructure.converter.FaqInfoConverter;
import com.gientech.ragcommon.index.request.FaqEsQuery;
import com.gientech.ragcommon.index.request.FaqUpdateReq;
import com.google.common.collect.Lists;
import com.google.common.collect.Maps;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;

import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.stream.Collectors;

import static com.gientech.ragcommon.index.enmus.FileFieldEnums.FAQ_TABLE_NAME_PREFIX;

import static com.gientech.ragcommon.index.constant.IndexConstant.FILE_TYPE_LIST;

@Slf4j
@Service
public class ChunnkDomainServiceImpl implements ChunnkDomainService {

    @Autowired
    private RemoteFileUtils remoteFileUtils;

    @Autowired
    private PyEsClient pyEsClient;

    @Autowired
    private PyMilvusClient pyMilvusClient;

    @Override
    public List<JSONObject> getByChunkId(String primitiveName, List<Long> pks) {
        FaqEsQuery query = buildQueryParam(FaqQueryReq.builder().primitiveName(primitiveName).pks(pks).pageNo(1).pageSize(10000).build());
        String resp = remoteFileUtils.pageListEs(JSONObject.toJSONString(query));
        JSONObject respJson = JSONObject.parseObject(resp);
        if (respJson.getInteger("code").equals(500)) {
            return null;
        }
        if (!Objects.equals(respJson.getInteger("code"), 200))
            throw new DomainException(ErrCodeEnum.FAQ_LIST_ERROR);
        JSONObject data = respJson.getJSONObject("data");
        if (Objects.isNull(data))
            return null;
        JSONArray resultData = data.getJSONArray("result_data");
        if (resultData == null || Objects.isNull(resultData))
            return null;
        List<JSONObject> dataList = Lists.newArrayList();
        resultData.forEach(result -> {
            JSONObject dataJson = (JSONObject) result;
            dataList.add(dataJson.getJSONObject("_source"));
        });
        return dataList;
    }

    @Override
    public Page<FaqInfo> pageList(FaqQueryReq faqQueryReq) {
        Page<FaqInfo> page = new PageDTO<>();
        List<FaqInfo> records = Lists.newArrayList();
        page.setRecords(records);
        Integer pageNo = faqQueryReq.getPageNo();
        Integer pageSize = faqQueryReq.getPageSize();
        FaqEsQuery query = buildQueryParam(faqQueryReq);
        String resp = remoteFileUtils.pageListEs(JSONObject.toJSONString(query));
        JSONObject respJson = JSONObject.parseObject(resp);
        if (respJson.getInteger("code").equals(500)) {
            return page;
        }
        if (!Objects.equals(respJson.getInteger("code"), 200))
            throw new DomainException(ErrCodeEnum.FAQ_LIST_ERROR);
        buildFaqResult(respJson, pageNo, pageSize, page, faqQueryReq.getExpand());
        return page;
    }

    @Override
    public Page<FaqInfo> pageFaqList(FaqQueryReq faqQueryReq) {
        Page<FaqInfo> page = new PageDTO<>();
        List<FaqInfo> records = Lists.newArrayList();
        page.setRecords(records);
        Integer pageNo = faqQueryReq.getPageNo();
        Integer pageSize = faqQueryReq.getPageSize();
        FaqEsQuery query = buildFaqQueryParam(faqQueryReq);
        String resp = remoteFileUtils.pageListEs(JSONObject.toJSONString(query));
        JSONObject respJson = JSONObject.parseObject(resp);
        if (respJson.getInteger("code").equals(500)) {
            return page;
        }
        if (!Objects.equals(respJson.getInteger("code"), 200))
            throw new DomainException(ErrCodeEnum.FAQ_LIST_ERROR);
        buildFaqResult(respJson, pageNo, pageSize, page, faqQueryReq.getExpand());
        return page;
    }

    private void buildFaqResult(JSONObject respJson, Integer pageNo, Integer pageSize, Page<FaqInfo> page, Boolean expand) {
        List<FaqInfo> records = page.getRecords();
        JSONObject data = respJson.getJSONObject("data");
        if (Objects.isNull(data))
            return;
        Integer totalCount = data.getInteger("total_count");
        page.setTotal(totalCount);

        if (!Objects.isNull(pageNo) && !Objects.isNull(pageSize)) {
            page.setCurrent(pageNo);
            page.setSize(pageSize);
            page.setPages((totalCount / pageSize) + ((totalCount % pageSize) > 0 ? 1 : 0));
        }

        JSONArray resultData = data.getJSONArray("result_data");
        if (resultData == null || Objects.isNull(resultData))
            return;
        resultData.forEach(result -> {
            JSONObject dataJson = (JSONObject) result;
            FaqInfo faq = new FaqInfo();
            JSONObject source = dataJson.getJSONObject("_source");
            faq.setPageContent(source.getString("page_content"));
            JSONObject metadata = source.getJSONObject("metadata");
            if (Objects.nonNull(expand) && expand)
                faq.setMetadata(metadata);
            if (!Objects.isNull(metadata)) {
                faq.setAnswer(metadata.getString("answer"));
                faq.setQuestion(metadata.getString("question"));
                faq.setPk(metadata.getLong("pk"));
                faq.setRelatedPk(metadata.getLong("related_pk"));
                faq.setFaqType(metadata.getInteger("faq_type"));
                faq.setStatus(metadata.getInteger("status"));
                faq.setFolderId(metadata.getLong("folder_id"));
                faq.setFaqFileId(metadata.getLong("file_id"));
                faq.setLabels(metadata.getList("labels", String.class));
                String sourceFile = metadata.getString("source");
                faq.setSourceFile(sourceFile);
                faq.setDocumentId(metadata.getLong("document_id"));
                if (StringUtils.isNotBlank(sourceFile))
                    faq.setSourceFileName(sourceFile.substring(sourceFile.lastIndexOf("/") + 1));
            }
            records.add(faq);
        });
    }


    @Override
    public Page<FaqInfo> pageListFromLocal(FaqQueryReq faqQueryReq) {
        String resp;
        FaqEsResponse faqEsResponse;
        FaqEsInfo data;

        Page<FaqInfo> faqInfoPage = new Page<>(faqQueryReq.getPageNo(), faqQueryReq.getPageSize());
        List<FaqInfo> records = Lists.newArrayList();
        FaqEsQuery query = buildQueryParam(faqQueryReq);
        Integer pageNo = faqQueryReq.getPageNo();

        do {
            resp = remoteFileUtils.pageListEs(query.toJSONString());
            faqEsResponse = JSONObject.parseObject(resp, FaqEsResponse.class);
            data = faqEsResponse.getData();
            records.addAll(FaqInfoConverter.INSTANCE.resultDataList2FaqInfoList(data.getResultData()));
            query.setPageNo(pageNo++);
        } while (!data.getResultData().isEmpty());

        faqInfoPage.setTotal(records.size());
        faqInfoPage.setPages(faqInfoPage.getTotal() / faqQueryReq.getPageSize() + 1);
        faqInfoPage.setRecords(records);
        return faqInfoPage;
    }


    @Override
    public List<FaqInfo> faqList(FaqQueryReq faqQueryReq) {
        Page<FaqInfo> faqPage = this.pageList(faqQueryReq);
        return faqPage.getRecords();
    }

    @Override
    public void deleteTable(String tableName) {
        //删除miluvs中的表
        remoteFileUtils.deleteMiluvsTable(tableName);
        //删除es中的表
        remoteFileUtils.deleteEsTable(tableName);
    }

    @Override
    public void delFiles(String tableName, List<String> filePaths) {
        if (CollectionUtils.isEmpty(filePaths))
            return;
        List<String> base64FilePaths = filePaths.stream()
                .map(filePath -> Base64.getEncoder().encodeToString(filePath.getBytes(StandardCharsets.UTF_8)))
                .collect(Collectors.toList());
        //删除miluvs中的文件
        delDelvector(tableName, base64FilePaths);
        //删除es中的文件
        delIndexFiles(tableName, base64FilePaths);
    }

    private void delIndexFiles(String tableName, List<String> filePaths) {
        JSONObject param = new JSONObject();
        param.put("index_name", tableName);
        if (!CollectionUtils.isEmpty(filePaths)) {
            param.put("col_name", "document_id");
            param.put("col_values", filePaths);
        }
        String resp = remoteFileUtils.delIndexFiles(JSONObject.toJSONString(param));
        JSONObject respJson = JSONObject.parseObject(resp);
        if (respJson.getInteger("code").equals(500)) {
            log.warn("数据不存在");
            return;
        }
        if (!Objects.equals(respJson.getInteger("code"), 200)) {
            throw new ApplicationException(ErrCodeEnum.DELETE_INDEX_ERROR.getErrCode(), respJson.getString("msg"));
        }
    }


    private void delDelvector(String primitiveName, List<String> filePaths) {
        JSONObject param = new JSONObject();
        param.put("collection_name", primitiveName);
        if (!CollectionUtils.isEmpty(filePaths)) {
            param.put("col_name", "document_id");
            param.put("col_values", filePaths);
        }
        remoteFileUtils.delDelvector(JSONObject.toJSONString(param));

    }

    private FaqEsQuery buildFaqQueryParam(FaqQueryReq faqQueryReq) {
        FaqEsQuery faqEsQuery = new FaqEsQuery();

        String primitiveName = faqQueryReq.getPrimitiveName();
        Long fileId = faqQueryReq.getFileId();
        List<Long> faqFileIds = faqQueryReq.getFaqFileIds();
        Integer pageNo = faqQueryReq.getPageNo();
        Integer pageSize = faqQueryReq.getPageSize();
        List<Long> pks = faqQueryReq.getPks();
        List<Long> relatedPks = faqQueryReq.getRelatedPks();
        List<Long> folderIds = faqQueryReq.getFolderIds();
        Integer faqType = faqQueryReq.getFaqType();
        //分页查询数据
        faqEsQuery.setIndexName(List.of(FileFieldEnums.FAQ_TABLE_NAME_PREFIX + primitiveName.toLowerCase(Locale.ROOT)));
        if (!Objects.isNull(pageNo) && !Objects.isNull(pageSize)) {
            faqEsQuery.setPageNo(pageNo);
            faqEsQuery.setPageSize(pageSize);
        }

        if (!Objects.isNull(fileId))
            faqEsQuery.setDocumentId(String.valueOf(fileId));

        List<JSONObject> searchConditions = Lists.newArrayList();
        if (!CollectionUtils.isEmpty(faqFileIds)) {
            JSONObject condition = new JSONObject();
            condition.put("file_id", faqFileIds);
            searchConditions.add(condition);
        }

        if (!CollectionUtils.isEmpty(folderIds)) {
            JSONObject condition = new JSONObject();
            condition.put("folder_id", folderIds);
            searchConditions.add(condition);
        }

        if (!CollectionUtils.isEmpty(pks)) {
            JSONObject condition = new JSONObject();
            condition.put("pk", pks);
            searchConditions.add(condition);
        }

        if (!Objects.isNull(relatedPks)) {
            JSONObject condition = new JSONObject();
            condition.put("related_pk", relatedPks);
            searchConditions.add(condition);
        }

        if (!Objects.isNull(faqType)) {
            JSONObject condition = new JSONObject();
            condition.put("faq_type", Arrays.asList(faqType));
            searchConditions.add(condition);
        }

        if (!searchConditions.isEmpty()) {
            faqEsQuery.setConditionLogicOperations("and");
        }

        faqEsQuery.setConditionJson(searchConditions);
        return faqEsQuery;
    }

    private FaqEsQuery buildQueryParam(FaqQueryReq faqQueryReq) {
        FaqEsQuery faqEsQuery = new FaqEsQuery();

        String primitiveName = faqQueryReq.getPrimitiveName();
        Long fileId = faqQueryReq.getFileId();
        List<Long> faqFileIds = faqQueryReq.getFaqFileIds();
        Integer pageNo = faqQueryReq.getPageNo();
        Integer pageSize = faqQueryReq.getPageSize();
        Integer status = faqQueryReq.getStatus();
        List<Long> pks = faqQueryReq.getPks();
        String fuzzy = faqQueryReq.getFuzzy();
        Integer faqType = faqQueryReq.getFaqType();
        List<Long> relatedPks = faqQueryReq.getRelatedPks();
        Long folderId = faqQueryReq.getFolderId();
        List<Long> folderIds = faqQueryReq.getFolderIds();
        Boolean isNeedFolderId = faqQueryReq.getIsNeedFolderId();
        //分页查询数据
        faqEsQuery.setIndexName(List.of(FileFieldEnums.FAQ_TABLE_NAME_PREFIX + primitiveName.toLowerCase(Locale.ROOT)));
        if (!Objects.isNull(pageNo) && !Objects.isNull(pageSize)) {
            faqEsQuery.setPageNo(pageNo);
            faqEsQuery.setPageSize(pageSize);
        }

        if (!Objects.isNull(fileId))
            faqEsQuery.setDocumentId(String.valueOf(fileId));

        List<JSONObject> searchConditions = Lists.newArrayList();

        if (Objects.isNull(isNeedFolderId) || isNeedFolderId) {
            JSONObject folderIdCondition = new JSONObject();
            folderIdCondition.put("folder_id", Objects.isNull(folderId) ? "" : folderId);
            searchConditions.add(folderIdCondition);
        }

        if (!CollectionUtils.isEmpty(faqFileIds)) {
            JSONObject condition = new JSONObject();
            condition.put("file_id", faqFileIds);
            searchConditions.add(condition);
        }

        if (!CollectionUtils.isEmpty(folderIds)) {
            JSONObject condition = new JSONObject();
            condition.put("folder_id", folderIds);
            searchConditions.add(condition);
        }

        if (!Objects.isNull(status)) {
            JSONObject condition = new JSONObject();
            condition.put("status", status);
            searchConditions.add(condition);
        }

        if (!CollectionUtils.isEmpty(pks)) {
            JSONObject condition = new JSONObject();
            condition.put("pk", pks);
            searchConditions.add(condition);
        }

        if (!Objects.isNull(relatedPks)) {
            JSONObject condition = new JSONObject();
            condition.put("related_pk", relatedPks);
            searchConditions.add(condition);
        }

        if (!Objects.isNull(faqType)) {
            JSONObject condition = new JSONObject();
            condition.put("faq_type", Arrays.asList(faqType));
            searchConditions.add(condition);
        }

        if (!searchConditions.isEmpty()) {
            faqEsQuery.setConditionLogicOperations("and");
        }

        if (StringUtils.isNotBlank(fuzzy)) {
            faqEsQuery.setConditionLogicOperations("or");
            JSONObject conditionQuestion = new JSONObject();
            conditionQuestion.put("page_content", List.of(fuzzy));
            searchConditions.add(conditionQuestion);

//            JSONObject conditionAnswer = new JSONObject();
//            conditionAnswer.put("answer", List.of(fuzzy));
//            searchConditions.add(conditionAnswer);
        }

        faqEsQuery.setConditionJson(searchConditions);
        return faqEsQuery;
    }

    @Override
    public void deleteFaq(String primitiveName, List<Long> fileIds, List<Long> faqFileIds) {
        //删除向量数据库中faq
        JSONObject delParam = new JSONObject();
        delParam.put("collection_name", FileFieldEnums.FAQ_TABLE_NAME_PREFIX + primitiveName);
//        delParam.put("col_name", "document_id");
//        delParam.put("col_values", fileIds.stream().map(id -> id.toString()).collect(Collectors.toList()));
        //condition_json
        List<JSONObject> searchConditions = Lists.newArrayList();

        if (!CollectionUtils.isEmpty(fileIds)) {
            JSONObject condition = new JSONObject();
            condition.put("document_id", fileIds.stream().map(fileId -> fileId.toString()).collect(Collectors.toList()));
            searchConditions.add(condition);
        }

        if (!CollectionUtils.isEmpty(faqFileIds)) {
            JSONObject condition = new JSONObject();
            condition.put("file_id", faqFileIds.stream().map(fileId -> fileId.toString()).collect(Collectors.toList()));
            searchConditions.add(condition);
        }

        delParam.put("condition_json", searchConditions);
        remoteFileUtils.faqDel(JSONObject.toJSONString(delParam));
        //删除es数据库中faq
        delParam.remove("collection_name");
        delParam.put("index_name", FileFieldEnums.FAQ_TABLE_NAME_PREFIX + primitiveName);
//        delParam.put("col_name", "document_id");
//        delParam.put("col_values", fileIds.stream().map(id -> id.toString()).collect(Collectors.toList()));
        String resp = remoteFileUtils.delIndexFiles(JSONObject.toJSONString(delParam));
        JSONObject respJson = JSONObject.parseObject(resp);
        if (Objects.equals(respJson.getInteger("code"), 500)) {
            return;
        }
        if (!Objects.equals(respJson.getInteger("code"), 200)) {
            throw new ApplicationException(ErrCodeEnum.DELETE_INDEX_ERROR.getErrCode(), respJson.getString("msg"));
        }
    }

    @Override
    public void updateChunkField(String primitiveName, List<Long> pks, String colName, Object colValue) {
        JSONObject faqReq = buildChangeFieldParam(primitiveName, pks, colName, colValue);
        remoteFileUtils.faqUpdateField(JSONObject.toJSONString(faqReq));
        //更新es中的数据
        String resp = remoteFileUtils.updateFieldteEs(JSONObject.toJSONString(faqReq));
        JSONObject respJson = JSONObject.parseObject(resp);
        if (!Objects.equals(respJson.getInteger("code"), 200))
            throw new ApplicationException(ErrCodeEnum.UPDATE_ES_ERROR);
    }

    private JSONObject buildChangeFieldParam(String tableName, List<Long> pks, String colName, Object colValue) {
        JSONObject faqReq = new JSONObject();
        faqReq.put("index_name", tableName);
        faqReq.put("pk", pks);
        faqReq.put("col_name", colName);
        faqReq.put("col_value", colValue);
        return faqReq;
    }

    @Override
    public void updateFaqBatch(String primitiveName, List<FaqUpdateReq> updateList) {
        if (CollectionUtils.isEmpty(updateList))
            return;
        JSONObject faqReq = new JSONObject();
        faqReq.put("document_list", updateList);
        faqReq.put("index_name", FAQ_TABLE_NAME_PREFIX + primitiveName);
        String req = JSONObject.toJSONString(faqReq);
        //更新milvus中的数据
        remoteFileUtils.faqUpdate(req);
        //更新es中的数据
        String resp = remoteFileUtils.faqUpdateEs(req);
        JSONObject respJson = JSONObject.parseObject(resp);
        if (!Objects.equals(respJson.getInteger("code"), 200))
            throw new ApplicationException(ErrCodeEnum.UPDATE_ES_ERROR);
    }


    @Override
    public List<FaqEsInfo.FaqEsMetadata> findFaqsByFolderIds(String indexName, String folderIds) {
        FaqEsResponse faqEsResponse = pyEsClient.searchByPage(PyLabelReq.getReqByFolderId(indexName, folderIds));
        if (faqEsResponse.getCode() == 200) {
            List<FaqEsInfo.FaqEsInfoResultData> resultData = faqEsResponse.getData().getResultData();
            if (CollectionUtils.isEmpty(resultData)) {
                return List.of();
            }
            List<FaqEsInfo.FaqEsMetadata> metadataList = resultData.stream().map(result -> result.getSource().getMetadata()).toList();
            return CollectionUtils.isEmpty(metadataList) ? List.of() : metadataList;
        }
        return List.of();
    }

    @Override
    public FaqEsInfo.FaqEsMetadata findFaqByPk(String indexName, Long pk) {
        FaqEsResponse faqEsResponse = pyEsClient.searchByPage(PyLabelReq.getReqByPk(FAQ_TABLE_NAME_PREFIX + indexName, pk));
        if (faqEsResponse.getCode() == 200) {
            if (Objects.isNull(faqEsResponse.getData())) {
                throw new ApplicationException(ErrCodeEnum.FAQ_NOT_EXIST_ERROR);
            }
            List<FaqEsInfo.FaqEsInfoResultData> resultData = faqEsResponse.getData().getResultData();
            if (CollectionUtils.isEmpty(resultData)) {
                return null;
            }
            return resultData.get(0).getSource().getMetadata();
        }
        throw new ApplicationException(ErrCodeEnum.FAQ_PARAM_ERROR.getErrCode(), faqEsResponse.getMsg());
    }

    @Override
    public void deleteFaqByPks(String primitiveName, List<Long> pks) {
        if (CollectionUtils.isEmpty(pks))
            return;
        //删除向量中的问答对
        JSONObject delParam = new JSONObject();
        delParam.put("collection_name", FAQ_TABLE_NAME_PREFIX + primitiveName);
        delParam.put("col_name", "pk");
        delParam.put("col_values", pks);
        remoteFileUtils.faqDel(JSONObject.toJSONString(delParam));
        //删除es中的问答对
        delParam = new JSONObject();
        delParam.put("index_name", FAQ_TABLE_NAME_PREFIX + primitiveName);
        delParam.put("pk_list", pks.stream().map(pk -> pk.toString()).collect(Collectors.toList()));
        String resp = remoteFileUtils.faqDelEs(JSONObject.toJSONString(delParam));
        JSONObject respJson = JSONObject.parseObject(resp);
        if (!Objects.equals(respJson.getInteger("code"), 200))
            throw new ApplicationException(ErrCodeEnum.FAQ_DELETE_ERROR);
    }

    @Override
    public void transferFaqBatch(String indexName, List<String> targetIds, Long targetFolderId) {
        if (CollectionUtils.isEmpty(targetIds)) {
            return;
        }
        PyLabelReq pyLabelReq = new PyLabelReq();
        pyLabelReq.setIndexName(FAQ_TABLE_NAME_PREFIX + indexName);
        pyLabelReq.setPk(targetIds);

        targetIds.forEach(targetId -> {
            Map<String, Object> colValue = Maps.newHashMap();
            colValue.put("folder_id", String.valueOf(targetFolderId));
            colValue.put("file_id", String.valueOf(targetFolderId));
            pyLabelReq.getUpdateConditionJson().put(targetId, colValue);
        });


        //FAQ_FILE其实还是FAQ，但FAQ是修改单个的
        PyEsResponse<Object> pyEsResponse = pyEsClient.updateById(pyLabelReq.getJSONString(BizTypeEnums.FAQ_FILE));
        if (pyEsResponse.getCode() != 200) {
            throw new ApplicationException(ErrCodeEnum.UPDATE_ES_ERROR);
        }
        PyMilvusResponse<Object> pyMilvusResponse = pyMilvusClient.updateByIdBatch(pyLabelReq.getJSONString(BizTypeEnums.FAQ_FILE));
        if (pyMilvusResponse.getCode() != 200) {
            throw new ApplicationException(ErrCodeEnum.UPDATE_MILVUS_ERROR);
        }
    }

    @Override
    public JSONObject getChunks(String primitiveName, String fileName, Integer pageNo, Integer pageSize) {
        JSONObject query = new JSONObject();
        query.put("index_name", Arrays.asList(primitiveName, FileFieldEnums.TABLE_CHUNKS_PREFIX + primitiveName));
        query.put("sort_field", "chunk_index");
        query.put("sort_mode", "asc");

        List<JSONObject> searchCondtions = new ArrayList<>();
        JSONObject condtion = new JSONObject();
        String originFileName = fileName;
        String fileType = fileName.substring(fileName.lastIndexOf(".") + 1);
        if (!FILE_TYPE_LIST.contains(fileType)) {
            String fileNamePrefix = fileName.substring(0, fileName.lastIndexOf("."));
            fileName = fileNamePrefix + ".pdf";
        }
        // R13-FIX-S6-01：非 pdf 类型曾经一律改写成 .pdf 去匹配 title，但实际 chunk 的 title 是原始文件名
        // （docx/pptx/xlsx 直读解析），导致"引用->原文"按文件 id 取回 0 个 chunk。这里同时匹配两种写法。
        if (!originFileName.equals(fileName)) {
            condtion.put("title", Arrays.asList(fileName, originFileName));
        } else {
            condtion.put("title", Arrays.asList(fileName));
        }
        searchCondtions.add(condtion);
        query.put("condition_json", searchCondtions);

        if (Objects.nonNull(pageNo) && Objects.nonNull(pageSize) && pageNo > 0 && pageSize > 0) {
            query.put("page_no", pageNo);
            query.put("page_num", pageSize);
        }

        String resp = remoteFileUtils.pageListEs(JSONObject.toJSONString(query));
        JSONObject respJson = JSONObject.parseObject(resp);
        if (respJson.getInteger("code").equals(500)) {
            return null;
        }
        if (!Objects.equals(respJson.getInteger("code"), 200))
            throw new ApplicationException(ErrCodeEnum.DOC_CHUNK_ERROR);
        return respJson;
    }
}
