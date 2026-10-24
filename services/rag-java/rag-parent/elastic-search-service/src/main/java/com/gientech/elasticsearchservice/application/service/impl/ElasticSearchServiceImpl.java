package com.gientech.elasticsearchservice.application.service.impl;

import co.elastic.clients.elasticsearch.ElasticsearchClient;
import co.elastic.clients.elasticsearch._types.Result;
import co.elastic.clients.elasticsearch._types.SortOrder;
import co.elastic.clients.elasticsearch._types.query_dsl.TermsQueryField;
import co.elastic.clients.elasticsearch.core.*;
import co.elastic.clients.elasticsearch.indices.ElasticsearchIndicesClient;
import com.gientech.elasticsearchservice.application.request.*;
import com.gientech.elasticsearchservice.application.service.ElasticSearchService;
import com.gientech.elasticsearchservice.document.FullTextDoc;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.util.List;

/**
 * @Description:
 * @Author: chenjuan
 * @Date: 2024/9/20 13:53
 */
@Service
@Slf4j
public class ElasticSearchServiceImpl implements ElasticSearchService {
    private final ElasticsearchClient elasticsearchClient;

    private final String DOCUMENT_ID_FIELD = "metadata.document_id";
    private final String PK_FIELD = "metadata.pk";

    @Autowired
    public ElasticSearchServiceImpl(ElasticsearchClient elasticsearchClient) {
        this.elasticsearchClient = elasticsearchClient;
    }

    @Override
    public boolean insertFullTextDoc(DocAddRequest<FullTextDoc> docAddRequest) throws IOException {
        IndexResponse response = elasticsearchClient.index(i -> i
                .index(docAddRequest.getIndexName())
                .id(docAddRequest.getDoc().getMetaData().getPk())
                .document(docAddRequest.getDoc())
        );
        if (response.result() == Result.Created) {
            return true;
        }
        return false;
    }

    @Override
    public boolean createIndex(String indexName) throws IOException {
        ElasticsearchIndicesClient indexClient = elasticsearchClient.indices();
        boolean isExist = indexClient.exists(req -> req.index(indexName)).value();
        if (!isExist) {
            indexClient.create(c -> c
                    .index(indexName)
            );
            log.info("create index {} success!", indexName);
        }
        return true;
    }

    @Override
    public boolean deleteIndex(String indexName) throws IOException {
        ElasticsearchIndicesClient indexClient = elasticsearchClient.indices();
        boolean isExist = indexClient.exists(req -> req.index(indexName)).value();
        if (isExist) {
            indexClient.delete(c -> c
                    .index(indexName)
            );
            log.info("delete index {} success!", indexName);
        }
        return true;
    }

    @Override
    public long deleteDocByMetaCol(DocDeleteRequest docDeleteRequest) throws IOException {
        DeleteByQueryRequest deleteByQueryRequest = DeleteByQueryRequest.of(d ->
                d.index(docDeleteRequest.getIndexName())
                        .query(q -> q.terms(
                                t -> t.field(docDeleteRequest.getColName())
                                        .terms(new TermsQueryField.Builder()
                                                .value(docDeleteRequest.getColValuesFieldValue()).build())
                        )));
        DeleteByQueryResponse response = elasticsearchClient.deleteByQuery(deleteByQueryRequest);
        return response.deleted();
    }

    private void insertDocsBatch(String indexName, List<FullTextDoc> fullTextDocs) throws IOException {
        // 构建 BulkRequest
        BulkRequest.Builder bulkRequestBuilder = new BulkRequest.Builder();
        for (FullTextDoc doc : fullTextDocs) {
            bulkRequestBuilder.operations(op -> op
                    .index(idx -> idx
                            .index(indexName)
                            .id(doc.getMetaData().getPk())
                            .document(doc)
                    )
            );
        }
        // 发送 BulkRequest
        BulkResponse bulkResponse = elasticsearchClient.bulk(bulkRequestBuilder.build());
        if (bulkResponse.errors()) {
            throw new RuntimeException(bulkResponse.items().get(0).error().reason());
        }
    }

    @Override
    public void updateDoc(DocUpdateRequest docUpdateRequest) throws IOException {
        List<String> docPkList = docUpdateRequest.getDocPkList();
        //删除旧文档
        deleteDocsByPkList(docUpdateRequest.getIndexName(), docPkList);
        //更新文档列表的时间
        docUpdateRequest.updateDocTime();
        insertDocsBatch(docUpdateRequest.getIndexName(),docUpdateRequest.getDocList());
    }

    private void deleteDocsByPkList(String indexName, List<String> docPkList) throws IOException {
        DocDeleteRequest docDeleteRequest = DocDeleteRequest.builder()
                .indexName(indexName)
                .colName(PK_FIELD)
                .colValues(docPkList).build();
        deleteDocByMetaCol(docDeleteRequest);
    }


    @Override
    public SearchResponse<FullTextDoc> queryByDocId(DocQueryRequest docQueryRequest) throws IOException {
        SearchResponse<FullTextDoc> response = elasticsearchClient.search(s -> s
                        .index(docQueryRequest.getIndexName())
                        .query(q -> q
                                .terms(t -> t
                                        .field(DOCUMENT_ID_FIELD)
                                        .terms(new TermsQueryField.Builder()
                                                .value(docQueryRequest.getDocIdsFieldValue()).build()
                                        )

                                )
                        ),
                FullTextDoc.class
        );
        return response;
    }

    @Override
    public SearchResponse<FullTextDoc> queryByCustomParam(DocCustomQueryRequest docCustomQueryRequest) throws IOException {
        SearchResponse<FullTextDoc> response = elasticsearchClient.search(s -> s
                        .index(docCustomQueryRequest.getIndexName())
                        .query(q -> q
                                .terms(t -> t
                                        .field(docCustomQueryRequest.getColName())
                                        .terms(new TermsQueryField.Builder()
                                                .value(docCustomQueryRequest.getColValuesFieldValue()).build()
                                        )

                                )
                        ).sort(sort -> sort
                                .field(f -> f
                                        .field(docCustomQueryRequest.getSortField())
                                        .order(docCustomQueryRequest.getSortMode())
                                )
                        ),
                FullTextDoc.class
        );
        return response;
    }

    @Override
    public SearchResponse<FullTextDoc> queryByPage(DocCustomQueryRequest docCustomQueryRequest) throws IOException {
        SearchResponse<FullTextDoc> response = elasticsearchClient.search(s -> s
                        .index(docCustomQueryRequest.getIndexName())
                        .query(q -> q
                                .terms(t -> t
                                        .field(docCustomQueryRequest.getColName())
                                        .terms(new TermsQueryField.Builder()
                                                .value(docCustomQueryRequest.getColValuesFieldValue()).build()
                                        )

                                )
                        ).sort(sort -> sort
                                .field(f -> f
                                        .field(docCustomQueryRequest.getSortField())
                                        .order(docCustomQueryRequest.getSortMode())
                                )
                        )
                        .from(docCustomQueryRequest.getPageNo())
                        .size(docCustomQueryRequest.getPageNum()),
                FullTextDoc.class
        );
        return response;
    }
}
