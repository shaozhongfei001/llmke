package com.gientech.sensitivewordsservice.application;

import com.gientech.ragcommon.sensitive.dto.SensitiveWordHitDTO;
import com.gientech.sensitivewordsservice.interfaces.request.SensitiveWordApiRequest;

import java.util.List;

public interface OpenApiAppService {

    /**
     * 检查文本是否命中敏感词
     * @param request 包含：原文本、指定的敏感词
     * @return true/false
     */
    Boolean checkHitsSensitiveWord(SensitiveWordApiRequest request);

    /**
     * 标记源文本中的敏感词
     * @param request 包含：原文本、指定的敏感词
     * @return true/false
     */
    List<SensitiveWordHitDTO> markSensitiveWords(SensitiveWordApiRequest request);

}
