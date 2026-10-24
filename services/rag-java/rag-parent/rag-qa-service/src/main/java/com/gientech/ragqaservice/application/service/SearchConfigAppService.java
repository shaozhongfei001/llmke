package com.gientech.ragqaservice.application.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.qa.dto.SearchConfigDTO;
import com.gientech.ragcommon.qa.request.SearchConfigAddReq;
import com.gientech.ragcommon.qa.request.SearchConfigQueryReq;
import com.gientech.ragcommon.qa.request.SearchConfigUpdateReq;
import com.gientech.ragcommon.qa.entity.Config;

import java.util.Set;

public interface SearchConfigAppService {
    /**
     * 添加配置
     *
     * @param searchConfigAddReq
     * @return
     */
    SearchConfigDTO addConfig(SearchConfigAddReq searchConfigAddReq);

    /**
     * 修改配置
     *
     * @param searchConfigUpdateReq
     * @return
     */
    Boolean update(SearchConfigUpdateReq searchConfigUpdateReq);

    /**
     * 更新配置状态
     *
     * @param configId
     * @param status
     * @return
     */
    Boolean updateStatus(Long configId, Integer status);

    /**
     * 通过id删除配置
     *
     * @param configId
     * @return
     */
    Boolean deleteById(Long configId);

    Config getConfigById(Long configId);

    /**
     * 设置为默认配置
     *
     * @param configId
     * @return
     */
    Boolean setDefault(Long configId);

    /**
     * 查询配置列表
     *
     * @param searchConfigQueryReq
     * @return
     */
    Page<SearchConfigDTO> searchList(SearchConfigQueryReq searchConfigQueryReq);

    /**
     * 查询配置列表（自己的助手+别人授权的助手）
     *
     * @param searchConfigQueryReq
     * @return
     */
    Page<SearchConfigDTO> searchAllList(SearchConfigQueryReq searchConfigQueryReq);

    /**
     * 查询配置列表(别人授权的数据)
     *
     * @param searchConfigQueryReq
     * @return
     */
    Page<SearchConfigDTO> shareList(SearchConfigQueryReq searchConfigQueryReq);

    /**
     * 查询配置列表 表查询逻辑：用户创建的配置 + 授予用户的配置 + 授予用户所属角色的配置；
     *
     * @param nameOrId
     * @return
     */
    Set<SearchConfigDTO> helperConfList(String nameOrId);

    int updateSensitiveWord(Long wordId);

    int updateKnowledgeBase(String baseName, String sourceName);

    int updateKbSourceName(String sourceName, String targetName);

    int updateDbIndex(String dbIndex);

    int renameDbIndex(String dbIndex, String newDbLabel, String oldDbLabel);

    /**
     * 查询配置助手创建者
     *
     * @param id
     * @return
     */
    String queryCreator(Long id);

    Boolean transferProperty(String owner, String receiver, boolean isClearKb);

    Object configItemLimit();

    /**
     * getReranks
     *
     * @return
     */
//    List<RerankDTO> getReranks();

    /**
     * 通过模型名称修改模型召回配置
     *
     * @param modelName
     * @param needTrace
     * @return
     */
    Boolean updateTrace(String modelName, Boolean needTrace);

    Boolean updateModelConfig(String modelName,Boolean thinking);

    String selectMultiModelName(String sessionId);

    SearchConfigDTO getById(Long configId);

    Boolean checkName(Long configId,String configName);

    Boolean replaceModel(String sourceModelName, String targetModelName);

    int selectReferenceByModelName(String modelName);
}
