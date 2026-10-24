package com.gientech.ragqaservice.application.remote;

import com.gientech.ragcommon.feign.FeignCustomConfig;
import com.gientech.ragcommon.global.CommonResponse;
import com.gientech.ragcommon.index.dto.ModelInfoDTO;
import com.gientech.ragcommon.index.dto.ModelSimpDTO;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;

@FeignClient(name = "rag-index-service",path = "index/modelInfo",configuration = FeignCustomConfig.class)
public interface ModelClient {

    /**
     * 通过模型名称查询
     * @param modeName
     * @return
     */
    @GetMapping("/getSimpByModeName")
    ModelSimpDTO getSimpByModeName(@RequestParam("modelName") String modeName);
}
