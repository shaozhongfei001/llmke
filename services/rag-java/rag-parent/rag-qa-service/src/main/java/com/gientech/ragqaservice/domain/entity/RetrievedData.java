package com.gientech.ragqaservice.domain.entity;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.gientech.ragcommon.qa.dto.Document;
import com.gientech.ragcommon.qa.dto.Faq;
import com.gientech.ragcommon.qa.dto.RetriveTagDTO;
import com.gientech.ragcommon.qa.dto.WebDocument;
import com.gientech.ragqaservice.interfaces.resp.RetrieveDoc;
import com.google.common.collect.Lists;
import lombok.Data;
import org.springframework.util.CollectionUtils;
import org.springframework.util.StringUtils;

import java.util.List;
import java.util.Objects;

/**
 * @Description:
 * @Author: chenjuan
 * @Date: 2024/9/27 11:29
 */
@Data
public class RetrievedData {
    private JSONObject data = new JSONObject();

    public static RetrievedData getDefault(String response) {
        RetrievedData retrievedDocument = new RetrievedData();
        JSONObject respObj = JSONObject.parseObject(response);
        retrievedDocument.setData(respObj.getJSONObject("data"));
        return retrievedDocument;
    }

    public String getDocumentString() {
        return data.getString("documents_list");
    }

    public String getTableSelectedDocumentString() {
        return data.getString("table_selected_list");
    }

    public String getFaqString() {
        return data.getString("faq_result_list");
    }

    public int getFaqSize() {
        JSONArray falList = data.getJSONArray("faq_result_list");
        if (Objects.isNull(falList))
            return 0;
        return falList.size();
    }

    public String getLogList() {
        return data.getString("log_list");
    }

//    public int getDocumentSize() {
//        JSONArray documentList = data.getJSONArray("documents_list");
//        if (Objects.isNull(documentList))
//            return 0;
//        return documentList.size();
//    }

    public Boolean existDocs() {
        JSONArray documentList = data.getJSONArray("documents_list");
        JSONArray webdocumentList = data.getJSONArray("web_documents_list");
        JSONArray databaseDocumentList = data.getJSONArray("database_documents");
        if(!CollectionUtils.isEmpty(documentList))
            return documentList.size() > 0;
        else if(!CollectionUtils.isEmpty(webdocumentList))
            return webdocumentList.size() > 0;
        else if(!CollectionUtils.isEmpty(databaseDocumentList))
            return databaseDocumentList.size() > 0;
        else
            return false;
    }

    public String getSimpleDocumentString() {
        return JSON.toJSONString(data.get("documents_list"), SimpleDocumentFilter.getDefault());
    }

    public List<Document> getSimpleDocuments(String minioUrl) {
        return getDocumentsByStr(minioUrl, getSimpleDocumentString());
    }

    public List<Document> getDocuments(String minioUrl) {
        return getDocumentsByStr(minioUrl, getDocumentString());
    }

    public List<Document> getTableSelectedDocuments(String minioUrl) {
        return getDocumentsByStr(minioUrl, getTableSelectedDocumentString());
    }

    public List<Faq> getFaqs() {
        List<Faq> faqs = data.getList("faq_result_list", Faq.class);
        return CollectionUtils.isEmpty(faqs) ? null : faqs;
    }

    public static List<Document> getDocumentsByStr(String minioUrl, String documentString) {
        if(StringUtils.hasText(documentString)){
            List<Document> documents = JSON.parseArray(documentString, Document.class);
            if (!CollectionUtils.isEmpty(documents))
                documents.forEach(d -> d.buildParsedFilePath(minioUrl));
            return documents;
        }
        return List.of();
    }

    public void removeFields(List<Document> docs) {
        docs.forEach(doc ->{
            doc.setPageContent(null);
            doc.setPicUrlList(null);
            JSONObject metadata = doc.getMetadata();
            metadata.remove("text_parent_id_list");
            metadata.remove("pic_children_id_list");
            metadata.remove("labels");
        });
    }


    public List<WebDocument> getWebDocumentList() {
        List<WebDocument> webDocumentList = data.getList("web_documents_list", WebDocument.class);
        return CollectionUtils.isEmpty(webDocumentList) ? null : webDocumentList;
    }

    public List<RetrieveDoc> getDatabaseDocuments() {
        List<RetrieveDoc> databaseDocuments = data.getList("database_documents", RetrieveDoc.class);
        return CollectionUtils.isEmpty(databaseDocuments) ? null : databaseDocuments;
    }
}
