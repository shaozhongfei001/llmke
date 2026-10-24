package com.gientech.ragindexservice.application.remote;

import com.gientech.ragcommon.feign.FeignPythonClientConfig;
import com.gientech.ragcommon.index.response.PyEsResponse;
import com.gientech.ragindexservice.application.remote.request.PyCollection;
import com.gientech.ragindexservice.application.remote.request.PyEsIndex;
import com.gientech.ragindexservice.domain.entity.FaqEsResponse;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;

@FeignClient(name = "py-es-client", url = "${remote.py-es-url}", configuration = FeignPythonClientConfig.class)
public interface PyEsClient {
    @PostMapping(value = "/update_by_id", consumes = MediaType.APPLICATION_JSON_VALUE)
    PyEsResponse<Object> updateById(@RequestBody String pyLabelReq);

    @PostMapping(value = "/search_by_page", consumes = MediaType.APPLICATION_JSON_VALUE)
    FaqEsResponse searchByPage(@RequestBody String pyLabelReq);

    @PostMapping(value = "/del_index", consumes = MediaType.APPLICATION_JSON_VALUE)
    PyEsResponse<Object> delIndex(@RequestBody PyEsIndex pyEsIndex);

    @PostMapping(value = "/del_doc_by_col", consumes = MediaType.APPLICATION_JSON_VALUE)
    PyEsResponse<Object> delDocByCol(@RequestBody PyEsIndex pyEsIndex);
}
