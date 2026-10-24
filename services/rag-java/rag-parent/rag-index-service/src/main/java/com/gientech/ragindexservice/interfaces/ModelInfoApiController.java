package com.gientech.ragindexservice.interfaces;

import com.gientech.ragcommon.global.CommonResponse;
import com.gientech.ragindexservice.application.service.ModelInfoAppService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * @Desc
 * @Author ZhenPanHong
 * @Date 2025/3/26 23:13
 */
@Tag(name = "模型OpenAPI接口")
@RestController
@RequestMapping("/api/modelInfo")
public class ModelInfoApiController {
    @Autowired
    private ModelInfoAppService modelInfoAppService;

    @Operation(summary = "查询文档创建者")
    @GetMapping("/queryCreator")
    public CommonResponse<String> queryCreator(@RequestParam(value = "id") Long id) {
        return CommonResponse.success(modelInfoAppService.queryCreator(id));
    }
}
