package com.gientech.sensitivewordsservice.domain.service.impl;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.infrastructure.exception.DomainException;
import com.gientech.sensitivewordsservice.domain.entity.SensitiveWords;
import com.gientech.sensitivewordsservice.domain.repository.SensitiveWordsRepository;
import com.gientech.sensitivewordsservice.domain.service.SensitiveWordsLibraryDomainService;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;

import java.util.*;

@Service
public class SensitiveWordsLibraryDomainServiceImpl implements SensitiveWordsLibraryDomainService {

    private static final Logger log = LoggerFactory.getLogger(SensitiveWordsLibraryDomainServiceImpl.class);
    @Autowired
    private SensitiveWordsRepository sensitiveWordsRepository;


    @Override
    public Long createWordsLibrary(SensitiveWords sensitiveWords) {
        if (Objects.nonNull(sensitiveWordsRepository.getByName(sensitiveWords.getName()))) {
            throw new DomainException("已存在同名敏感词库");
        }
        sensitiveWords.setGmtCreate(new Date());
        sensitiveWords.setGmtModified(new Date());
        sensitiveWords.setStatus(1);
        return sensitiveWordsRepository.add(sensitiveWords);
    }

    @Override
    public Boolean deleteWordsLibrary(Long id) {
        SensitiveWords oldSensitiveWords = sensitiveWordsRepository.getById(id);
        if (Objects.isNull(oldSensitiveWords)) {
            throw new DomainException("敏感词库不存在");
        }
        SensitiveWords sensitiveWords = new SensitiveWords();
        sensitiveWords.setId(id);
        sensitiveWords.setStatus(-1);
        sensitiveWords.setGmtModified(new Date());
        return sensitiveWordsRepository.updateById(sensitiveWords);
    }

    @Override
    public SensitiveWords updateWordsLibraryById(SensitiveWords sensitiveWords) {
        SensitiveWords dbSensitiveWords = sensitiveWordsRepository.getById(sensitiveWords.getId());
        if (Objects.isNull(dbSensitiveWords)) {
            throw new DomainException("敏感词库不存在");
        }
        SensitiveWords byNameSensitiveWords = sensitiveWordsRepository.getByName(sensitiveWords.getName());
        if (Objects.nonNull(byNameSensitiveWords) && !byNameSensitiveWords.getId().equals(sensitiveWords.getId())) {
            throw new DomainException("已存在同名敏感词库");
        }
        sensitiveWords.setGmtModified(new Date());
        sensitiveWordsRepository.updateById(sensitiveWords);
        return sensitiveWordsRepository.getById(sensitiveWords.getId());
    }

    @Override
    public SensitiveWords queryWordsLibraryById(Long id) {
        SensitiveWords oldSensitiveWords = sensitiveWordsRepository.getById(id);
        if (Objects.isNull(oldSensitiveWords)) {
            throw new DomainException("敏感词库不存在");
        }
        return oldSensitiveWords;
    }

    @Override
    public Page<SensitiveWords> pageQuery(String name, List<Long> ids, Integer pageNo, Integer pageSize) {
        return sensitiveWordsRepository.page(name, ids, pageNo, pageSize);
    }

    @Override
    public List<SensitiveWords> getListByIds(List<Long> ids) {
        return sensitiveWordsRepository.getListByIds(ids);
    }

    /**
     * 根据词库id修改敏感词
     *
     * @param libraryId 词库id
     * @param words     敏感词列表
     * @return 成/败
     */
    @Override
    public Boolean updateSensitiveWords(Long libraryId, LinkedHashSet<String> words) {
        SensitiveWords sensitiveWords = new SensitiveWords();
        sensitiveWords.setId(libraryId);
        sensitiveWords.setWords(words);
        sensitiveWords.setGmtModified(new Date());
        return sensitiveWordsRepository.updateById(sensitiveWords);
    }

    /**
     * 根据词库id，覆盖旧的敏感词，追加新的敏感词，最终存入到words字段
     *
     * @param sensitiveWords 旧的敏感词库信息
     * @param words          不分新旧的铭感词列表
     * @return 成功/失败
     */
    @Override
    public Boolean coverOldAndReceiveNewSensitiveWords(SensitiveWords sensitiveWords, LinkedHashSet<String> words) {
        try {
            LinkedHashSet<String> toSaveWordsSet = new LinkedHashSet<>();
            if (!CollectionUtils.isEmpty(sensitiveWords.getWords()))
                toSaveWordsSet.addAll(sensitiveWords.getWords());
            toSaveWordsSet.addAll(words);
            sensitiveWords.setWords(toSaveWordsSet);
            sensitiveWords.setGmtModified(new Date());
            return sensitiveWordsRepository.updateById(sensitiveWords);
        } catch (Exception e) {
            log.error("coverOldAndReceiveNewSensitiveWords error sensitiveWords {},ex:{}", sensitiveWords, e);
            throw new DomainException("敏感词保存失败");

        }
    }
}
