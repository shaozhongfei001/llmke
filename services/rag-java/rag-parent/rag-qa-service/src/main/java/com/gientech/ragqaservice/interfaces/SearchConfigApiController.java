package com.gientech.ragqaservice.interfaces;

import com.gientech.ragcommon.global.CommonResponse;
import com.gientech.ragqaservice.application.service.SearchConfigAppService;
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
 * @Date 2025/3/26 23:23
 */
@Tag(name = "查询配置openapi接口")
@RestController
@RequestMapping("/api/search/config")
public class SearchConfigApiController {

    @Autowired
    private SearchConfigAppService searchConfigAppService;

    @Operation(summary = "查询配置助手创建者")
    @GetMapping("/queryCreator")
    public CommonResponse<String> queryCreator(@RequestParam(value = "id") Long id){
        return CommonResponse.success(searchConfigAppService.queryCreator(id));
    }
}
