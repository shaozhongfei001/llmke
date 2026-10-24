package com.gientech.elasticsearchservice.application.service;

import co.elastic.clients.elasticsearch.core.IndexResponse;
import co.elastic.clients.elasticsearch.core.SearchResponse;
import com.gientech.elasticsearchservice.application.request.*;
import com.gientech.elasticsearchservice.document.FullTextDoc;

import java.io.IOException;

/**
 * @Description:
 * @Author: chenjuan
 * @Date: 2024/9/20 13:53
 */
public interface ElasticSearchService {

    boolean insertFullTextDoc(DocAddRequest<FullTextDoc> docAddRequest) throws IOException;

    boolean createIndex(String indexName) throws IOException;

    boolean deleteIndex(String indexName) throws IOException;

    long deleteDocByMetaCol(DocDeleteRequest docDeleteRequest) throws IOException;

    void updateDoc(DocUpdateRequest docUpdateRequest) throws IOException;

    SearchResponse<FullTextDoc> queryByDocId(DocQueryRequest docQueryRequest) throws IOException;

    SearchResponse<FullTextDoc> queryByCustomParam(DocCustomQueryRequest docCustomQueryRequest) throws IOException;

    SearchResponse<FullTextDoc> queryByPage(DocCustomQueryRequest docCustomQueryRequest) throws IOException;
}
