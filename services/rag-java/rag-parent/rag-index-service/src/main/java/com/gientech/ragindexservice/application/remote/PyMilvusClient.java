package com.gientech.ragindexservice.application.remote;

import com.gientech.ragcommon.feign.FeignPythonClientConfig;
import com.gientech.ragcommon.index.response.PyMilvusResponse;
import com.gientech.ragindexservice.application.remote.request.*;
import com.gientech.ragindexservice.application.remote.response.PyMilvusResultData;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;

@FeignClient(name = "py-milvus-client", url = "${remote.py-milvus-url}", configuration = FeignPythonClientConfig.class)
public interface PyMilvusClient {
    @PostMapping(value = "/update_by_id", consumes = MediaType.APPLICATION_JSON_VALUE)
    PyMilvusResponse<Object> updateById(@RequestBody String pyLabelReq);

    @PostMapping(value = "/update_by_id_batch", consumes = MediaType.APPLICATION_JSON_VALUE)
    PyMilvusResponse<Object> updateByIdBatch(@RequestBody String pyLabelReq);

    @PostMapping(value = "/get_doc_by_col", consumes = MediaType.APPLICATION_JSON_VALUE)
    PyMilvusResponse<Object> getDocByCol(@RequestBody String pyLabelReq);

    @PostMapping(value = "/update_doc", consumes = MediaType.APPLICATION_JSON_VALUE)
    PyMilvusResponse<Object> updateDoc(@RequestBody PyMilvusUpdateDocRequest request);

    @PostMapping(value = "/get_doc_page", consumes = MediaType.APPLICATION_JSON_VALUE)
    PyMilvusResponse<PyMilvusResultData> getDocPage(@RequestBody PyMilvusPageRequest request);

    @PostMapping(value = "/del_doc_by_col", consumes = MediaType.APPLICATION_JSON_VALUE)
    PyMilvusResponse<Object> delDocByCol(@RequestBody PyCollection request);

    @PostMapping(value = "/create_milvus_collection", consumes = MediaType.APPLICATION_JSON_VALUE)
    PyMilvusResponse<Object> createMilvusCollection(@RequestBody PyCollection request);

    @PostMapping(value = "/insert_vector_documents_custom", consumes = MediaType.APPLICATION_JSON_VALUE)
    PyMilvusResponse<Object> insertVectorDocumentsCustom(@RequestBody PyMilvusInsertRequest request);

    @PostMapping(value = "/migrate_milvus_collection", consumes = MediaType.APPLICATION_JSON_VALUE)
    PyMilvusResponse<Object> migrateMilvusCollection(@RequestBody PyMigrateRequest request);
}
