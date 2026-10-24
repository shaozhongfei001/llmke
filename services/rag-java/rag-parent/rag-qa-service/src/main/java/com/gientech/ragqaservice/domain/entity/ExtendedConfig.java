package com.gientech.ragqaservice.domain.entity;

import cn.hutool.core.bean.BeanUtil;
import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONObject;
import com.alibaba.nacos.shaded.com.google.common.collect.Maps;
import com.gientech.ragcommon.index.dto.FilePathDTO;
import com.gientech.ragcommon.qa.dto.Document;
import com.gientech.ragcommon.qa.dto.WebDocument;
import com.gientech.ragqaservice.application.service.entity.AiHistory;
import com.gientech.ragqaservice.interfaces.resp.RetrieveDoc;
import com.gientech.ragqaservice.interfaces.resp.SqlMetaData;
import lombok.Data;
import org.apache.commons.lang3.StringUtils;
import org.springframework.context.annotation.Bean;
import org.springframework.util.CollectionUtils;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Objects;

import static com.gientech.ragcommon.qa.constant.AIConstant.*;

/**
 * @Description:
 * @Author: chenjuan
 * @Date: 2024/9/26 18:24
 */
@Data
public class ExtendedConfig implements Cloneable {
    private JSONObject config = new JSONObject();

    public void init(String configJson) {
        config = JSON.parseObject(configJson);
    }

    public static ExtendedConfig getDefault(String configJson) {
        ExtendedConfig extendedConfig = new ExtendedConfig();
        extendedConfig.init(configJson);
        return extendedConfig;
    }

    public Boolean enabledLlm(){
        Boolean enabledLlm = config.getBoolean(ENABLED_LLM);
        return !Objects.isNull(enabledLlm) && enabledLlm;
    }

    public Boolean getNeedRecall(){
        Boolean needRecall = config.getBoolean(NEED_TRACE_SOURCE);
        return !Objects.isNull(needRecall) && needRecall;
    }

    public Boolean getEnabledTableSelect(){
        Boolean enabledTableSelect = config.getBoolean(ENABLED_TABLE_SELECT);
        return !Objects.isNull(enabledTableSelect) && enabledTableSelect;
    }


    public String getConfigJSONString() {
        return JSON.toJSONString(config);
    }

    public String getKnowledgeBaseName() {
        return config.getString(KNOWLEDGE_BASE_NAME);
    }


    public void setKnowledgeBaseName(String knowledgeBaseName) {
        config.put(KNOWLEDGE_BASE_NAME, knowledgeBaseName);
    }


    public void convertKBN2Array(){
        String knowledgeBaseName = getKnowledgeBaseName();
        if(StringUtils.isNotBlank(knowledgeBaseName)){
            config.put(KNOWLEDGE_BASE_NAME,knowledgeBaseName.split(";"));
        }else {
            config.put(KNOWLEDGE_BASE_NAME, new ArrayList<>());
        }
    }


    public void setStream(boolean isStream) {
        config.put(STREAM, isStream);
    }

    public String getModelName() {
        return config.getString(MODEL_NAME);
    }

    public void setChatHistory(List<AiHistory> historyMapList){
        config.put(CHAT_HISTORY, historyMapList);
    }

    public void setDatabaseDocuments(List<RetrieveDoc> databaseDocuments) {
        config.put(DATABASE_DOCUMENTS, databaseDocuments);
    }

    public void setTableResultData(SqlMetaData.TableResultData tableResultData) {
        config.put(TABLE_RESULT_DATA, tableResultData);
    }

    public void setModelName(String modelName) {
        config.put(MODEL_NAME, modelName);
    }

    public void setFilePathsAndRemoveKb(List<String> filePaths) {
        config.put(KNOWLEDGE_BASE_NAME,null);
        config.put(KNOWLEDGE_BASE_NAME_SOURCE,null);
        config.put(FILE_PATHS, filePaths);
    }

    public String getQuery() {
        return config.getString(QUERY);
    }

    public void setQuery(String query) {
        config.put(QUERY, query);
    }

    public String getRewrittenQuery() {
        return config.getString(REWRITTEN_QUERY);
    }

    public void setRewrittenQuery(String rewrittenQuery) {
        config.put(REWRITTEN_QUERY, rewrittenQuery);
    }

    public String getTopK() {
        return config.getString(TOP_K);
    }

    public void setTopK(String topK) {
        config.put(TOP_K, topK);
    }

    public String getReRank(){
        return config.getString(ENABLED_RERANK);
    }

    public void setReRank(String reRank){
        config.put(ENABLED_RERANK,reRank);
    }

    public String getEnabledFaq(){
        return config.getString(ENABLED_FAQ);
    }

    public void setEnableFaq(String enableFaq){
        config.put(ENABLED_FAQ,enableFaq);
    }

    public Integer getMaxRound(){
        return config.getInteger(MAX_ROUND);
    }

    public void setMaxRound(Integer enableFaq){
        config.put(MAX_ROUND,enableFaq);
    }

    public void setDocuments(List<Document> documents){
        config.put(DOCUMENTS,documents);
    }

    public void setDocuments(List<Document> documents, List<WebDocument> webDocumentList){
        config.put(DOCUMENTS,documents);
        config.put(WEB_DOCUMENTS_LIST,webDocumentList);
    }

    public String getDocuments(){
        Map<String,String> docs = Maps.newHashMap();
        docs.put(DOCUMENTS,config.getString(DOCUMENTS));
        docs.put(WEB_DOCUMENTS_LIST,config.getString(WEB_DOCUMENTS_LIST));
        return JSON.toJSONString(docs);
    }

    public String removeFieldAndGetDos(){
        Map<String,List> docs = Maps.newHashMap();
        List<Document> documents = JSON.parseArray(config.getString(DOCUMENTS),Document.class);
        documents.forEach(doc ->{
            doc.setPageContent(null);
            doc.setPicUrlList(null);
            JSONObject metadata = doc.getMetadata();
            metadata.remove(TEXT_PARENT_ID_LIST);
            metadata.remove(PIC_CHILDREN_ID_LIST);
            metadata.remove(LABELS);
        });
        docs.put(DOCUMENTS,documents);
        docs.put(WEB_DOCUMENTS_LIST,config.getList(WEB_DOCUMENTS_LIST,WebDocument.class));
        return JSON.toJSONString(docs);
    }


    @Override
    public Object clone() throws CloneNotSupportedException {
        ExtendedConfig extendedConfig = (ExtendedConfig) super.clone();
        extendedConfig.config = this.config.clone();
        return extendedConfig;
    }

    public void setCurrentFiles(List<FilePathDTO> currentFiles) {
        config.put(CURRENTFILES, currentFiles);
    }

    public void setTopN() {
        if(!StringUtils.isEmpty(getTopK()))
            config.put(TOP_N,getTopK());
    }

    public void removeFields(List<String> fields) {
        if(!CollectionUtils.isEmpty(fields))
            fields.forEach(field -> config.remove(field));
    }
}
