//package com.gientech.ragindexservice.domain.service.impl;
//
//import com.alibaba.fastjson2.JSONObject;
//import com.gientech.ragcommon.global.ErrCodeEnum;
//import com.gientech.ragcommon.index.enmus.FileFieldEnums;
//import com.gientech.ragcommon.infrastructure.exception.DomainException;
//import com.gientech.ragindexservice.domain.entity.KnowledgeBaseList;
//import com.gientech.ragindexservice.domain.service.FileDomainService;
//import com.gientech.ragindexservice.infrastructure.RemoteFileUtils;
//import com.gientech.start.minio.properties.MinioConfigProperties;
//import lombok.extern.slf4j.Slf4j;
//import org.springframework.beans.factory.annotation.Autowired;
//import org.springframework.stereotype.Service;
//import org.springframework.util.CollectionUtils;
//import java.nio.charset.StandardCharsets;
//import java.util.Base64;
//import java.util.List;
//import java.util.stream.Collectors;
//
//@Slf4j
//@Service
//public class FileDomainServiceImpl implements FileDomainService {
//
//    @Autowired
//    private RemoteFileUtils remoteFileUtils;
//
//    @Autowired
//    private MinioConfigProperties minioConfig;
//
//    @Override
//    public void delIndexFiles(String primitiveName, List<String> filePaths) {
//        JSONObject param = new JSONObject();
//        param.put("index_name", primitiveName);
//        if (!CollectionUtils.isEmpty(filePaths)) {
//            param.put("col_name", "document_id");
//            param.put("col_values",
//                    filePaths.stream()
//                            .map(filePath -> Base64.getEncoder().encodeToString(filePath.getBytes(StandardCharsets.UTF_8)))
//                            .collect(Collectors.toList()));
//        }
//        remoteFileUtils.delIndexFiles(JSONObject.toJSONString(param));
//    }
//
//    @Override
//    public void delDelvector(String primitiveName, List<String> filePaths) {
//        JSONObject param = new JSONObject();
//        param.put("collection_name", primitiveName);
//        if (!CollectionUtils.isEmpty(filePaths)) {
//            param.put("col_name", "document_id");
//            param.put("col_values", filePaths.stream()
//                    .map(filePath -> Base64.getEncoder().encodeToString(filePath.getBytes(StandardCharsets.UTF_8)))
//                    .collect(Collectors.toList()));
//        }
//        String resp = remoteFileUtils.delDelvector(JSONObject.toJSONString(param));
//        JSONObject respJson = JSONObject.parseObject(resp);
//        if (respJson.getInteger("code").equals(500)) {
//            log.warn("数据不存在");
//            return;
//        }
//        if(!Objects.equals(respJson.getInteger("code"),200))
//            throw new DomainException(ErrCodeEnum.DELETE_INDEX_ERROR);
//    }
//
//    @Override
//    public void deleteFAQ(String primitiveName, List<Long> ids) {
//        //删除向量数据库中faq
//        JSONObject delParam = new JSONObject();
//        delParam.put("collection_name", FileFieldEnums.FAQ_TABLE_NAME_PREFIX + primitiveName);
//        delParam.put("col_name", "document_id");
//        delParam.put("col_values", ids.stream().map(id -> id.toString()).collect(Collectors.toList()));
//        remoteFileUtils.faqDel(JSONObject.toJSONString(delParam));
//        //删除es数据库中faq
//        delParam.put("index_name", FileFieldEnums.FAQ_TABLE_NAME_PREFIX + primitiveName);
//        delParam.put("col_name", "document_id");
//        delParam.put("col_values", ids.stream().map(id -> id.toString()).collect(Collectors.toList()));
//        remoteFileUtils.delIndexFiles(JSONObject.toJSONString(delParam));
//    }
//}
