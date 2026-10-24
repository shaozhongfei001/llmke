package com.gientech.ragindexservice.interfaces;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.index.dto.ModelInfoDTO;
import com.gientech.ragcommon.index.dto.ModelSimpDTO;
import com.gientech.ragcommon.index.request.ModelInfoCreateReq;
import com.gientech.ragcommon.index.request.ModelInfoQueryReq;
import com.gientech.ragcommon.index.request.ModelInfoUpdateReq;
import com.gientech.ragcommon.operation.annotation.OperationLog;
import com.gientech.ragindexservice.application.service.ModelInfoAppService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * @Desc 模型管理 前端控制器
 * @Author ZhenPanHong
 * @Date 2025/3/5 13:30
 */
@Tag(name = "模型管理接口")
@RestController
@RequestMapping("/modelInfo")
public class ModelInfoController {

    @Autowired
    private ModelInfoAppService modelInfoAppService;


    @Operation(summary = "检测模型")
    @PostMapping("/check")
    @OperationLog(operateType = "检测模型")
    public Boolean check() {
        return modelInfoAppService.check();
    }

    @Operation(summary = "通过id查询模型状态 0:不可用；1可用；2；检测中，3:检测中")
    @GetMapping("/getStatusById")
    public Integer getStatusById(@RequestParam(value = "id") Long id) {
        return modelInfoAppService.getStatusById(id);
    }

    @Operation(summary = "创建模型")
    @PostMapping("/create")
    @OperationLog(operateType = "创建模型")
    public ModelInfoDTO createModelInfo(@Validated @RequestBody ModelInfoCreateReq modelInfoCreateReq) {
        return modelInfoAppService.createModelInfo(modelInfoCreateReq);
    }

    @Operation(summary = "删除模型")
    @DeleteMapping("/delete")
    @OperationLog(operateType = "删除模型")
    public Boolean deleteById(@Parameter(name = "id", description = "模型id", required = true) @RequestParam("id") Long id) {
        return modelInfoAppService.deleteById(id);
    }

    @Operation(summary = "更新")
    @PutMapping("/update")
    @OperationLog(operateType = "编辑模型")
    public ModelInfoDTO update(@Validated @RequestBody ModelInfoUpdateReq modelInfoUpdateReq) {
        return modelInfoAppService.updateById(modelInfoUpdateReq);
    }

    @Operation(summary = "分页查询模型列表")
    @GetMapping("/page")
    @OperationLog(operateType = "分页查询模型列表")
    public Page<ModelInfoDTO> page(ModelInfoQueryReq modelInfoQueryReq) {
        return modelInfoAppService.page(modelInfoQueryReq);
    }

    @Operation(summary = "查询模型列表(不分页)")
    @GetMapping("/list")
    @OperationLog(operateType = "查询模型列表(不分页)")
    public List<ModelInfoDTO> list(ModelInfoQueryReq modelInfoQueryReq) {
        return modelInfoAppService.list(modelInfoQueryReq);
    }

    @Operation(summary = "通过id查询模型信息")
    @GetMapping("/getById")
    public ModelInfoDTO getById(@Parameter(name = "id", description = "模型id", required = true) @RequestParam(value = "id") Long id) {
        return modelInfoAppService.getById(id);
    }

    /**
     * 获取模型类型集合
     *
     * @return
     */
    @Operation(summary = "获取模型类型集合")
    @GetMapping(value = "/getModelTypes")
    public List<Map> getModelTypes() {
        return modelInfoAppService.getModelTypes();
    }

    @Operation(summary = "获取模型传输协议集合")
    @GetMapping(value = "/getModelProtocols")
    public List<Map> getModelProtocols() {
        return modelInfoAppService.getModelProtocols();
    }


    @Operation(summary = "共享模型列表数据(分页)")
    @GetMapping("/share/page")
    @OperationLog(operateType = "共享模型列表数据(分页)")
    public Page<ModelInfoDTO> sharePage(ModelInfoQueryReq modelInfoQueryReq) {
        return modelInfoAppService.sharePage(modelInfoQueryReq);
    }

    @Operation(summary = "自建和共享模型列表数据(分页)")
    @GetMapping("/allPage")
    @OperationLog(operateType = "自建和共享模型列表数据(分页)")
    public Page<ModelInfoDTO> allPage(ModelInfoQueryReq modelInfoQueryReq) {
        return modelInfoAppService.allPage(modelInfoQueryReq);
    }

    @Operation(summary = "通过模型名称查询")
    @GetMapping("/getByModelName")
    public ModelInfoDTO getByModeName(@RequestParam("modelName") String modeName) {
        return modelInfoAppService.getByModelName(modeName);
    }

    @Operation(summary = "通过模型名称获取模型")
    @GetMapping("/getSimpByModeName")
    public ModelSimpDTO getSimpByModeName(@RequestParam("modelName") String modeName) {
        return modelInfoAppService.getSimpByModeName(modeName);
    }

    @Operation(summary = "转移模型资源")
    @GetMapping("/transferProperty")
    public Boolean transferModelProperty(@RequestParam("owner") String owner, @RequestParam("receiver") String receiver) {
        return modelInfoAppService.transferProperty(owner, receiver);
    }

    @Operation(summary = "替换模型")
    @GetMapping("/replaceModel")
    public Boolean replaceModel(@RequestParam("sourceModelId") Long sourceModelId, @RequestParam("targetModelId") Long targetModelId) {
        return modelInfoAppService.replaceModel(sourceModelId, targetModelId);
    }

    @GetMapping("/checkModelReference")
    public int checkModelReference(@RequestParam("modelName") String modelName) {
        return modelInfoAppService.checkModelReference(modelName);
    }


}
