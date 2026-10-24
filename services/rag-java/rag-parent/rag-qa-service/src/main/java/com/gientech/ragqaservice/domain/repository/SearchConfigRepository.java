package com.gientech.ragqaservice.domain.repository;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.index.enmus.SearchConfigScopeEnums;
import com.gientech.ragcommon.qa.entity.Config;

import java.util.List;

public interface SearchConfigRepository {

    List<Config> getConfigByUser();

    Config getDefaultConfig(int status);

    Boolean updateStatus(Long id, int status);

    Config insert(Config config);

    Boolean update(Config config);

    Boolean deleteById(Long configId);

    Page<Config> list(List<Long> ids, String fuzzy, Long pageNo, Long pageSize, SearchConfigScopeEnums scope);

    Boolean updateDefault(Long id, int defaultCode);

    Config getById(Long id);

    Config getConfigById(Long id);

    int updateSensitiveWords(Long wordId);

    int updateKnowledgeBase(String baseName);

    int updateSourceKnowledgeBase(String sourceName);

    int updateDbIndex(String dbIndex);

    int renameDbIndex(String dbIndex, String newDbLabel, String oldDbLabel);

    int updateKbSourceName(String sourceName, String targetName);

    int transferProperty(String owner, String receiver, boolean isClearKb);

    Boolean updateTrace(String modelName, Boolean needTrace);

    Boolean updateModelConfig(String modelName, Boolean thinking);

    Config getConfigByName(String userName,String configName);

    Boolean replaceModel(String sourceModelName, String targetModelName);

    int selectReferenceByModelName(String modelName);
}
