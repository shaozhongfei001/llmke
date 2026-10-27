package com.gientech.ragqaservice.domain.service.impl;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.index.enmus.SearchConfigScopeEnums;
import com.gientech.ragcommon.qa.enmus.ConfigDefaultEnums;
import com.gientech.ragcommon.qa.entity.Config;
import com.gientech.ragqaservice.domain.repository.SearchConfigRepository;
import com.gientech.ragqaservice.domain.service.SearchConfigDomainService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

/**
 * <p>
 * 问题查询配置表 服务实现类
 * </p>
 *
 * @author wudf
 * @since 2024-11-14
 */
@Service
public class SearchConfigDomainServiceImpl implements SearchConfigDomainService {

    @Autowired
    private SearchConfigRepository searchConfigRepository;

    @Override
    public Config addConfig(Config config) {
        return searchConfigRepository.insert(config);
    }

    @Override
    public Config getConfigById(Long id) {
        return searchConfigRepository.getById(id);
    }

    @Override
    public Boolean update(Config config) {
        return searchConfigRepository.update(config);
    }

    @Override
    public Boolean deleteById(Long configId) {
        return searchConfigRepository.deleteById(configId);
    }

    @Override
    public List<Config> getConfigByUser() {
        return searchConfigRepository.getConfigByUser();
    }

    @Override
    public Config getDefaultConfig() {
        return searchConfigRepository.getDefaultConfig(ConfigDefaultEnums.YES.getCode());
    }

    @Override
    public Config getSystemDefaultConfig() {
        return searchConfigRepository.getSystemDefaultConfig(ConfigDefaultEnums.YES.getCode());
    }

    @Override
    public Boolean updateStatus(Long id, int status) {
        return searchConfigRepository.updateStatus(id, status);
    }

    @Override
    public Page<Config> list(List<Long> ids, String fuzzy, Long pageNo, Long pageSize, SearchConfigScopeEnums scope) {
        return searchConfigRepository.list(ids, fuzzy, pageNo, pageSize, scope);
    }

    @Override
    public Boolean updateDefault(Long id, int defaultCode) {
        return searchConfigRepository.updateDefault(id, defaultCode);
    }

    @Override
    public int updateSensitiveWord(Long wordId) {
        return searchConfigRepository.updateSensitiveWords(wordId);
    }

    @Override
    public int updateKnowledgeBase(String baseName) {
        return searchConfigRepository.updateKnowledgeBase(baseName);
    }

    @Override
    public int updateSourceKnowledgeBase(String sourceName) {
        return searchConfigRepository.updateSourceKnowledgeBase(sourceName);
    }

    @Override
    public int updateKbSourceName(String sourceName, String targetName) {
        return searchConfigRepository.updateKbSourceName(sourceName, targetName);
    }

    @Override
    public Boolean updateTrace(String modelName, Boolean needTrace) {
        return searchConfigRepository.updateTrace(modelName, needTrace);
    }

    @Override
    public int updateDbIndex(String dbIndex) {
        return searchConfigRepository.updateDbIndex(dbIndex);
    }

    @Override
    public int renameDbIndex(String dbIndex, String newDbLabel, String oldDbLabel) {
        return searchConfigRepository.renameDbIndex(dbIndex, newDbLabel, oldDbLabel);
    }

    @Override
    public Boolean updateModelConfig(String modelName, Boolean thinking) {
        return searchConfigRepository.updateModelConfig(modelName, thinking);
    }

    @Override
    public Config getConfigByName(String userName,String configName) {
        return searchConfigRepository.getConfigByName(userName,configName);
    }

    @Override
    public Boolean transferProperty(String owner, String receiver, boolean isClearKb) {
        return searchConfigRepository.transferProperty(owner, receiver, isClearKb) > 0;
    }

    @Override
    public Boolean replaceModel(String sourceModelName, String targetModelName) {
        return searchConfigRepository.replaceModel(sourceModelName, targetModelName);
    }

    @Override
    public int selectReferenceByModelName(String modelName) {
        return searchConfigRepository.selectReferenceByModelName(modelName);
    }
}
