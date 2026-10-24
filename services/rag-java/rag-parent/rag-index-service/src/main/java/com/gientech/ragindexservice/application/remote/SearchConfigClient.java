package com.gientech.ragindexservice.application.remote;

import com.gientech.ragcommon.feign.FeignCustomConfig;
import com.gientech.ragcommon.qa.entity.Config;
import io.swagger.v3.oas.annotations.Operation;
import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestParam;

/**
 * @Description:
 * @Author: chenjuan
 * @Date: 2024/9/10 17:10
 */
@FeignClient(name = "rag-qa-service", path = "qa/search/config", configuration = FeignCustomConfig.class)
public interface SearchConfigClient {

    @GetMapping("/updateKnowledgeBase")
    int updateKnowledgeBase(@RequestParam("baseName") String baseName, @RequestParam("sourceName") String sourceName);

    @GetMapping("/updateKbSourceName")
    int updateKbSourceName(@RequestParam("sourceName") String sourceName, @RequestParam("targetName") String targetName);

    @Operation(summary = "通过模型名称修改模型召回配置")
    @PutMapping("/updateTrace")
    Boolean updateTrace(@RequestParam("modelName") String modelName, @RequestParam("needTrace") Boolean needTrace);

    @Operation(summary = "通过模型名称修改模型配置trace thinking")
    @PutMapping("/updateModelConfig")
    Boolean updateModelConfig(@RequestParam("modelName") String modelName, @RequestParam("thinking") Boolean thinking);


    @GetMapping("/{id}")
    Config getConfigById(@PathVariable("id") Long configId);


    @Operation(summary = "通过绘话id查询多模态模型名称")
    @GetMapping("/selectMultiModelName")
    String selectMultiModelName(@RequestParam("sessionId") String sessionId);

    @GetMapping("/replaceModel")
    Boolean replaceModel(@RequestParam("sourceModelName") String sourceModelName, @RequestParam("targetModelName") String targetModelName);

    @GetMapping("/selectReferenceByModelName")
    int selectReferenceByModelName(@RequestParam("modelName") String modelName);
}
