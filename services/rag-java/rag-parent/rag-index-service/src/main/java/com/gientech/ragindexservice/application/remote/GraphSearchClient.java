package com.gientech.ragindexservice.application.remote;

import com.gientech.ragcommon.feign.FeignCustomConfig;
import com.gientech.ragcommon.global.CommonResponse;
import com.gientech.ragcommon.graph.dto.GraphInstanceDTO;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;

import java.util.List;
import java.util.Map;

@FeignClient(name = "rag-graph-service", path = "graph/search",configuration = FeignCustomConfig.class)
public interface GraphSearchClient {

    @GetMapping("/instances")
    Map<Long, GraphInstanceDTO> instance(@RequestParam("spaceName") String spaceName, @RequestParam("fileIds") List<Long> fileIds);
}
