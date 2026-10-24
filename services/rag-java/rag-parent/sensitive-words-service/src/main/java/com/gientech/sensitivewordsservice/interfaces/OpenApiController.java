package com.gientech.sensitivewordsservice.interfaces;


import com.gientech.ragcommon.sensitive.dto.SensitiveWordHitDTO;
import com.gientech.sensitivewordsservice.application.OpenApiAppService;
import com.gientech.sensitivewordsservice.interfaces.request.SensitiveWordApiRequest;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Tag(name = "敏感词对外服务")
@RestController
@RequestMapping("/api")
public class OpenApiController {

    @Autowired
    private OpenApiAppService openApiAppService;

    @Operation(summary = "判断输入文本是否涉及敏感词，返回true/false")
    @PostMapping("/check_hit_sensitive_words/v1")
    public Map<String,Object> checkHitsSensitiveWord(@RequestBody @Validated SensitiveWordApiRequest request) {
        Boolean success = openApiAppService.checkHitsSensitiveWord(request);
        HashMap<String, Object> result = new HashMap<>();
        result.put("isHit", success);
        return result;
    }


    @Operation(summary = "标记文章敏感词，返回敏感词及其上下文")
    @PostMapping("/mark_sensitive_words/v1")
    public List<SensitiveWordHitDTO> markSensitiveWords(@RequestBody @Validated SensitiveWordApiRequest request) {
        return openApiAppService.markSensitiveWords(request);
    }


}
