package com.gientech.sensitivewordsservice.domain.service;


import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.sensitivewordsservice.domain.entity.SensitiveWords;

import java.util.LinkedHashSet;
import java.util.List;

public interface SensitiveWordsLibraryDomainService {


    Long createWordsLibrary(SensitiveWords sensitiveWords);


    Boolean deleteWordsLibrary(Long id);


    SensitiveWords updateWordsLibraryById(SensitiveWords sensitiveWords);


    SensitiveWords queryWordsLibraryById(Long id);

    Page<SensitiveWords> pageQuery(String name, List<Long> ids, Integer pageNo, Integer pageSize);

    List<SensitiveWords> getListByIds(List<Long> ids);


    /**
     * 根据词库id修改敏感词，修改words字段值
     * @param libraryId 词库id
     * @param words 敏感词列表
     * @return
     */
    Boolean updateSensitiveWords(Long libraryId, LinkedHashSet<String> words);

    /**
     * 根据词库id，覆盖旧的敏感词，追加新的敏感词，最终存入到words字段
     * @param sensitiveWords  旧的敏感词库信息
     * @param words 不分新旧的铭感词列表
     * @return 成功/失败
     */
    Boolean coverOldAndReceiveNewSensitiveWords(SensitiveWords sensitiveWords, LinkedHashSet<String> words);

}
