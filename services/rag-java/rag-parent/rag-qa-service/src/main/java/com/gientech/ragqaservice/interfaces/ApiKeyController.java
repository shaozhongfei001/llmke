package com.gientech.ragqaservice.interfaces;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.qa.request.ApiKeyQueryReq;
import com.gientech.ragqaservice.application.service.ApiKeyInfoAppService;
import com.gientech.ragcommon.qa.dto.ApiKeyInfoDTO;
import com.gientech.ragcommon.qa.request.SaveApiKeyInfoReq;
import com.gientech.ragcommon.qa.request.UpdateApiKeyInfoReq;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

@Tag(name = "apikey的信息")
@RestController
@RequestMapping("/apiKey")
public class ApiKeyController {

    @Autowired
    private ApiKeyInfoAppService apiKeyInfoAppService;

    @Operation(summary = "分页查询")
    @GetMapping()
    public Page<ApiKeyInfoDTO> list(ApiKeyQueryReq apiKeyQueryReq) {
        return apiKeyInfoAppService.list(apiKeyQueryReq);
    }

    @Operation(summary = "通过id查询数据")
    @GetMapping("{id}")
    public ApiKeyInfoDTO queryApiKeyInfo(@PathVariable("id") Long id) {
        return apiKeyInfoAppService.findById(id);
    }

    @Operation(summary = "保存")
    @PostMapping()
    public Boolean saveApiKeyInfo(@RequestBody SaveApiKeyInfoReq apiKeyInfoReq) {
        return apiKeyInfoAppService.save(apiKeyInfoReq);
    }

    @Operation(summary = "通过id更新")
    @PutMapping()
    public Boolean updateApiKeyInfo(@RequestBody UpdateApiKeyInfoReq updateLogTestReq) {
        return apiKeyInfoAppService.updateById(updateLogTestReq);
    }

    @Operation(summary = "通过id删除")
    @DeleteMapping("{id}")
    public Boolean deleteApiKeyInfoById(@PathVariable("id") Long id) {
        return apiKeyInfoAppService.deleteById(id);
    }

    @Operation(summary = "校验API是否合法")
    @PostMapping("/checkApiKey")
    public Boolean checkApiKey(@RequestParam("apiKey") String apiKey) {
        return apiKeyInfoAppService.checkApiKey(apiKey);
    }

}
