package com.gientech.ragqaservice.domain.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.index.enmus.SearchConfigScopeEnums;
import com.gientech.ragcommon.qa.entity.Config;

import java.util.List;

/**
 * <p>
 * 问题查询配置表 服务类
 * </p>
 *
 * @author wudf
 * @since 2024-11-14
 */
public interface SearchConfigDomainService {

    Config addConfig(Config config);

    Config getConfigById(Long id);

    List<Config> getConfigByUser();

    Config getDefaultConfig();

    /** R14-C-FIX-15b：系统默认助手（不限 create_by，取 is_default=1 且未删除的那一行）。 */
    Config getSystemDefaultConfig();

    Boolean updateStatus(Long id, int status);

    Boolean update(Config config);

    Boolean deleteById(Long configId);

    Page<Config> list(List<Long> ids, String fuzzy, Long pageNo, Long pageSize, SearchConfigScopeEnums scope);

    Boolean updateDefault(Long id, int defaultCode);

    int updateSensitiveWord(Long wordId);

    int updateKnowledgeBase(String baseName);

    int updateSourceKnowledgeBase(String sourceName);

    int updateKbSourceName(String sourceName, String targetName);

    Boolean transferProperty(String owner, String receiver, boolean isClearKb);

    Boolean updateTrace(String modelName, Boolean needTrace);

    int updateDbIndex(String dbIndex);

    int renameDbIndex(String dbIndex, String newDbLabel, String oldDbLabel);

    Boolean updateModelConfig(String modelName, Boolean thinking);

    Config getConfigByName(String userName,String configName);

    Boolean replaceModel(String sourceModelName, String targetModelName);

    int selectReferenceByModelName(String modelName);
}
