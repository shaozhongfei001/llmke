package com.gientech.ragqaservice.domain.repository;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.index.enmus.SearchConfigScopeEnums;
import com.gientech.ragcommon.qa.entity.Config;

import java.util.List;

public interface SearchConfigRepository {

    List<Config> getConfigByUser();

    Config getDefaultConfig(int status);

    /**
     * R14-C-FIX-15b：系统默认助手（**不限 create_by**）。
     * getDefaultConfig 是按 create_by 过滤的"个人默认"，普通用户没有自有助手时必然取不到，
     * 于是"回落到系统默认助手"这条裁决落不了地（会让非 admin 用户一律 400）。
     * 这里取 is_default=1 且未删除的那一行——DB 层已用函数唯一索引保证至多一行。
     */
    Config getSystemDefaultConfig(int status);

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
