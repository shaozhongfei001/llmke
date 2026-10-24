package com.gientech.sensitivewordsservice.application.impl;

import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.ragcommon.sensitive.dto.SensitiveWordHitDTO;
import com.gientech.sensitivewordsservice.application.OpenApiAppService;
import com.gientech.sensitivewordsservice.domain.entity.SensitiveWords;
import com.gientech.sensitivewordsservice.domain.service.SensitiveWordsLibraryDomainService;
import com.gientech.sensitivewordsservice.infrastructure.NacosConfig;
import com.gientech.ragcommon.sensitive.utils.AnsjParseWordUtils;
import com.gientech.sensitivewordsservice.interfaces.request.SensitiveWordApiRequest;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;
import java.util.*;

@Slf4j
@Service
public class OpenApiAppServiceImpl implements OpenApiAppService {

    @Autowired
    AnsjParseWordUtils ansjParseWordUtils;

    @Autowired
    private NacosConfig nacosConfig;


    @Autowired
    private SensitiveWordsLibraryDomainService sensitiveWordsLibraryDomainService;


    @Override
    public Boolean checkHitsSensitiveWord(SensitiveWordApiRequest request) {
        HashSet<String> sensitiveWordsSet = getTargetSensitiveWords(request.getLibraryIds());
        return ansjParseWordUtils.checkHitSensitiveWords(request.getSourceText(), sensitiveWordsSet);
    }

    @Override
    public List<SensitiveWordHitDTO> markSensitiveWords(SensitiveWordApiRequest request) {
        HashSet<String> sensitiveWordsSet = getTargetSensitiveWords(request.getLibraryIds());
        return ansjParseWordUtils.markSensitiveWord(request.getSourceText(), sensitiveWordsSet);
    }

    /**
     * 获取指定敏感词列表
     * @param libraryIds 用户指定的敏感词库
     * @return 敏感词列表
     */
    private HashSet<String> getTargetSensitiveWords(List<Long> libraryIds) {
        if (CollectionUtils.isEmpty(libraryIds)) {
            //如果用户未指定敏感词库，使用默认敏感词库
            libraryIds = nacosConfig.getSensitiveWordsId();
        }
        List<SensitiveWords> sensWordList = sensitiveWordsLibraryDomainService.getListByIds(libraryIds);
        if (CollectionUtils.isEmpty(sensWordList)) {
            throw new ApplicationException("指定无效敏感词库");
        }
        HashSet<String> sensitiveWordsSet = new LinkedHashSet<>();
        sensWordList.forEach(word->sensitiveWordsSet.addAll(word.getWords()));
        return sensitiveWordsSet;
    }

}
