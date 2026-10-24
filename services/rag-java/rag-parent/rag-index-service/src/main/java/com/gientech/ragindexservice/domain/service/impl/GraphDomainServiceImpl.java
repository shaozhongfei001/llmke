package com.gientech.ragindexservice.domain.service.impl;

import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.ragindexservice.domain.service.GraphDomainService;
import com.gientech.ragindexservice.infrastructure.RemoteGraphUtils;
import lombok.extern.slf4j.Slf4j;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;

import java.util.List;
import java.util.Objects;

import static com.gientech.ragcommon.index.enmus.FileFieldEnums.GRAPH_BASE;
import static com.gientech.ragcommon.index.enmus.FileFieldEnums.GRAPH_ENTITY_PREFIX;

@Slf4j
@Service
public class GraphDomainServiceImpl implements GraphDomainService {

    @Autowired
    private RemoteGraphUtils remoteGraphUtils;

    @Override
    public Boolean delGraphSpace(String spaceName, Long fileId) {
        JSONObject req = new JSONObject();
        req.put("space_name",spaceName);
        if(!Objects.isNull(fileId)){
            JSONObject conditionJson = new JSONObject();
            conditionJson.put("file_id",fileId);
            req.put("condition_json",conditionJson);
        }
        String resp = remoteGraphUtils.delSpace(JSONObject.toJSONString(req));
        JSONObject respJson = JSONObject.parseObject(resp);
        if (respJson.getInteger("code").equals(500)) {
            log.warn("图数据不存在");
            return false;
        }
        if(!Objects.equals(respJson.getInteger("code"),200)) {
            throw new ApplicationException(ErrCodeEnum.DELETE_GRAPH_ERROR.getErrCode(), respJson.getString("msg"));
        }
        return true;
    }

    @Override
    public Boolean delGraphEntity(String spaceName,List<String> fileIds,List<String> fileNames) {
        JSONObject req = new JSONObject();
        req.put("db_name",GRAPH_BASE);
        req.put("index_name",GRAPH_ENTITY_PREFIX + spaceName);
        if(!CollectionUtils.isEmpty(fileIds) && !CollectionUtils.isEmpty(fileNames)){
            JSONObject conditionjson = new JSONObject();
            conditionjson.put("file_id",fileIds);
            conditionjson.put("title",fileNames);
            req.put("update_condition_json",conditionjson);
        }
        String resp = remoteGraphUtils.delSpaceEntity(JSONObject.toJSONString(req));
        JSONObject respJson = JSONObject.parseObject(resp);
        if (respJson.getInteger("code").equals(500)) {
            log.warn("图数据不存在");
            return false;
        }
        if(!Objects.equals(respJson.getInteger("code"),200)) {
            throw new ApplicationException(ErrCodeEnum.DELETE_GRAPH_ERROR.getErrCode(), respJson.getString("msg"));
        }
        return true;
    }
}
