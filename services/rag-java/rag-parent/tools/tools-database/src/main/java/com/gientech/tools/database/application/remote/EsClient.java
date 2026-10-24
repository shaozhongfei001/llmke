package com.gientech.tools.database.application.remote;

import com.gientech.ragcommon.feign.FeignPythonClientConfig;
import com.gientech.ragcommon.index.response.PyEsResponse;
import com.gientech.tools.database.interfaces.request.EsDelColRequest;
import com.gientech.tools.database.interfaces.request.EsDelRequest;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;

/**
 * @author: shirleychen
 * @date 2025/9/16 17:24
 * @description
 */
@FeignClient(name = "es-client", url = "${remote.py-es-url}", configuration = FeignPythonClientConfig.class)
public interface EsClient {
    @PostMapping("/del_index")
    PyEsResponse<Object> delIndex(@RequestBody EsDelRequest esDelRequest);

    @PostMapping("/del_doc_by_col")
    PyEsResponse<Object> delDocByCol(@RequestBody EsDelColRequest esDelColRequest);
}

