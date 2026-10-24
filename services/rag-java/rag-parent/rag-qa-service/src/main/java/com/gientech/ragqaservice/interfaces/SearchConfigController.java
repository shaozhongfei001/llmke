package com.gientech.ragqaservice.interfaces;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.operation.annotation.OperationLog;
import com.gientech.ragcommon.qa.dto.SearchConfigDTO;
import com.gientech.ragcommon.qa.entity.Config;
import com.gientech.ragcommon.qa.request.SearchConfigAddReq;
import com.gientech.ragcommon.qa.request.SearchConfigQueryReq;
import com.gientech.ragcommon.qa.request.SearchConfigUpdateReq;
import com.gientech.ragqaservice.application.service.SearchConfigAppService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.Set;

/**
 * <p>
 * 问题查询配置表 前端控制器
 * </p>
 *
 * @author wudf
 * @since 2024-06-18
 */
@Tag(name = "查询配置接口")
@RestController
@RequestMapping("/search/config")
public class SearchConfigController {

    @Autowired
    private SearchConfigAppService searchConfigAppService;

    @Operation(summary = "添加查询配置")
    @PostMapping("/add")
    @OperationLog(operateType = "创建配置助手")
    public SearchConfigDTO addConfig(@RequestBody @Validated SearchConfigAddReq searchConfigAddReq) {
        return searchConfigAppService.addConfig(searchConfigAddReq);
    }

    @Operation(summary = "修改配置")
    @PutMapping("/update")
    @OperationLog(operateType = "修改配置助手")
    public Boolean update(@RequestBody @Validated SearchConfigUpdateReq searchConfigUpdateReq) {
        return searchConfigAppService.update(searchConfigUpdateReq);
    }

    @Operation(summary = "修改配置状态")
    @PutMapping("/updateStatus")
    public Boolean updateStatus(
            @Parameter(name = "configId", description = "配置id", required = true)
            @RequestParam("configId") Long configId,
            @Parameter(name = "status", description = "状态 0:禁用；1:正常 ", required = true)
            @RequestParam("status") Integer status) {
        return searchConfigAppService.updateStatus(configId, status);
    }

    @Operation(summary = "通过id删除配置")
    @DeleteMapping("/deleteById")
    @OperationLog(operateType = "删除配置助手")
    public Boolean deleteById(
            @Parameter(name = "configId", description = "配置id", required = true)
            @RequestParam("configId") Long configId) {
        return searchConfigAppService.deleteById(configId);
    }

    @Operation(summary = "根据id获取助手配置")
    @GetMapping("/{id}")
    @OperationLog(operateType = "根据id获取助手配置")
    public Config getConfigById(@PathVariable("id") Long configId) {
        return searchConfigAppService.getConfigById(configId);
    }


    @Operation(summary = "设为默认配置")
    @PutMapping("/setDefault")
    public Boolean setDefault(
            @Parameter(name = "configId", description = "配置id", required = true)
            @RequestParam("configId") Long configId) {
        return searchConfigAppService.setDefault(configId);
    }

    @Operation(summary = "查询配置列表")
    @GetMapping("/searchList")
    public Page<SearchConfigDTO> searchList(SearchConfigQueryReq searchConfigQueryReq) {
        return searchConfigAppService.searchList(searchConfigQueryReq);
    }

    @Operation(summary = "共享配置列表(别人授权的数据)")
    @GetMapping("/share/list")
    public Page<SearchConfigDTO> shareList(SearchConfigQueryReq searchConfigQueryReq) {
        return searchConfigAppService.shareList(searchConfigQueryReq);
    }

    @Operation(summary = "查询配置列表(自己的助手+别人共享的助手）")
    @GetMapping("/searchAllList")
    public Page<SearchConfigDTO> searchAllList(SearchConfigQueryReq searchConfigQueryReq) {
        return searchConfigAppService.searchAllList(searchConfigQueryReq);
    }

    @Operation(summary = "查询组手配置列表")
    @GetMapping("/helper/list")
    public Set<SearchConfigDTO> helperConfList(@RequestParam(value = "nameOrId", required = false) String nameOrId) {
        return searchConfigAppService.helperConfList(nameOrId);
    }

    @Operation(summary = "通过id更新")
    @GetMapping("/updateSensitiveWord/{id}")
    public int updateSensitiveWord(@PathVariable("id") Long wordId) {
        return searchConfigAppService.updateSensitiveWord(wordId);
    }

    @Operation(summary = "通过名称更新")
    @GetMapping("/updateKnowledgeBase")
    public int updateKnowledgeBase(@RequestParam("baseName") String baseName, @RequestParam("sourceName") String sourceName) {
        return searchConfigAppService.updateKnowledgeBase(baseName, sourceName);
    }

    @GetMapping("/updateKbSourceName")
    public int updateKbSourceName(@RequestParam("sourceName") String sourceName, @RequestParam("targetName") String targetName) {
        return searchConfigAppService.updateKbSourceName(sourceName, targetName);
    }

    //deleteDbIndex
    @GetMapping("/updateDbIndex")
    public int updateDbIndex(@RequestParam("dbIndex") String dbIndex) {
        return searchConfigAppService.updateDbIndex(dbIndex);
    }

    @GetMapping("/renameDbIndex")
    public int renameDbIndex(@RequestParam("dbIndex") String dbIndex, @RequestParam("newDbLabel") String newDbLabel, @RequestParam("oldDbLabel") String oldDbLabel) {
        return searchConfigAppService.renameDbIndex(dbIndex, newDbLabel, oldDbLabel);
    }

    @Operation(summary = "通过模型名称修改模型召回配置")
    @PutMapping("/updateTrace")
    public Boolean updateTrace(@RequestParam("modelName") String modelName, @RequestParam("needTrace") Boolean needTrace) {
        return searchConfigAppService.updateTrace(modelName, needTrace);
    }

    @Operation(summary = "通过模型名称修改模型配置 thinking")
    @PutMapping("/updateModelConfig")
    public Boolean updateModelConfig(@RequestParam("modelName") String modelName, @RequestParam("thinking") Boolean thinking) {
        return searchConfigAppService.updateModelConfig(modelName, thinking);
    }

    @Operation(summary = "转移助手")
    @GetMapping("/transferProperty")
    public Boolean transferSearchConfigProperty(@RequestParam("owner") String owner, @RequestParam("receiver") String receiver) {
        return searchConfigAppService.transferProperty(owner, receiver, true);
    }

    @Operation(summary = "助手配置项限制")
    @GetMapping("/configItemLimit")
    public Object configItemLimit() {
        return searchConfigAppService.configItemLimit();
    }

    @Operation(summary = "通过绘话id查询多模态模型名称")
    @GetMapping("/selectMultiModelName")
    public String selectMultiModelName(@RequestParam("sessionId") String sessionId) {
        return searchConfigAppService.selectMultiModelName(sessionId);
    }

    @Operation(summary = "通过id查询组手配置")
    @GetMapping("/getById")
    public SearchConfigDTO getById(@RequestParam(value = "configId") Long configId) {
        return searchConfigAppService.getById(configId);
    }


    @Operation(summary = "校验助手名称是否存在")
    @GetMapping("/checkName")
    public Boolean checkName(@RequestParam(value = "configId", required = false) Long configId, @RequestParam(value = "configName") String configName) {
        return searchConfigAppService.checkName(configId, configName);
    }

    @Operation(summary = "替换助手中的模型")
    @GetMapping("/replaceModel")
    public Boolean replaceModel(@RequestParam("sourceModelName") String sourceModelName, @RequestParam("targetModelName") String targetModelName) {
        return searchConfigAppService.replaceModel(sourceModelName, targetModelName);
    }

    @Operation(summary = "查找助手中的模型引用")
    @GetMapping("/selectReferenceByModelName")
    public int selectReferenceByModelName(@RequestParam("modelName") String modelName) {
        return searchConfigAppService.selectReferenceByModelName(modelName);
    }
}
