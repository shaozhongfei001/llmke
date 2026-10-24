package com.gientech.ragqaservice.application.service.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.collection.CollUtil;
import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONObject;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.auth.dto.PrivilegeDTO;
import com.gientech.ragcommon.auth.enums.PrivilegeTypeEnums;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.index.enmus.PermissionEnums;
import com.gientech.ragcommon.index.enmus.SearchConfigScopeEnums;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.ragcommon.qa.dto.SearchConfigDTO;
import com.gientech.ragcommon.qa.enmus.ConfigDefaultEnums;
import com.gientech.ragcommon.qa.enmus.ConfigStatusEnums;
import com.gientech.ragcommon.qa.entity.Config;
import com.gientech.ragcommon.qa.request.SearchConfigAddReq;
import com.gientech.ragcommon.qa.request.SearchConfigQueryReq;
import com.gientech.ragcommon.qa.request.SearchConfigUpdateReq;
import com.gientech.ragqaservice.application.remote.AuthClient;
import com.gientech.ragqaservice.application.remote.ModelClient;
import com.gientech.ragqaservice.application.service.SearchConfigAppService;
import com.gientech.ragqaservice.domain.entity.Dialogue;
import com.gientech.ragqaservice.domain.service.DialogueDomainService;
import com.gientech.ragqaservice.domain.service.SearchConfigDomainService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.context.config.annotation.RefreshScope;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.CollectionUtils;
import org.springframework.util.StringUtils;

import java.util.*;
import java.util.function.Function;
import java.util.stream.Collectors;

import static com.gientech.ragcommon.qa.constant.AIConstant.*;

@RefreshScope
@Slf4j
@Service
public class SearchConfigAppServiceImpl implements SearchConfigAppService {

    @Autowired
    private SearchConfigDomainService searchConfigDomainService;

    @Autowired
    private AuthClient authClient;

    @Value("${search.config-limit:}")
    private String searchConfigLimit;

    @Autowired
    private ModelClient modelClient;

    @Autowired
    private DialogueDomainService dialogueDomainService;

//    @Value("${search.rerank}")
//    private String searchConfigRerank;


    @Override
    public String selectMultiModelName(String sessionId) {
        Dialogue dialogue = dialogueDomainService.getDialogueBySessionId(sessionId);
        if (Objects.isNull(dialogue))
            return null;
        Config config = dialogue.getConfig();
        if (Objects.isNull(config))
            return null;
        String configJson = config.getConfigJson();
        if (StringUtils.hasText(configJson)) {
            JSONObject json = JSON.parseObject(configJson);
            return json.getString(MULTI_MODEL_NAME);
        }
        return null;
    }

    @Transactional
    @Override
    public SearchConfigDTO addConfig(SearchConfigAddReq searchConfigAddReq) {
        Integer isDefault = searchConfigAddReq.getIsDefault();
        if (!Objects.isNull(isDefault) && Objects.equals(ConfigDefaultEnums.YES.getCode(), isDefault)) {
            Config defaultConfig = searchConfigDomainService.getDefaultConfig();
            if (!Objects.isNull(defaultConfig))
                searchConfigDomainService.updateDefault(defaultConfig.getId(), ConfigDefaultEnums.NO.getCode());
        } else {
            searchConfigAddReq.setIsDefault(ConfigDefaultEnums.NO.getCode());
        }
        Config config = searchConfigDomainService.addConfig(BeanUtil.copyProperties(searchConfigAddReq, Config.class));
        return BeanUtil.copyProperties(config, SearchConfigDTO.class);
    }

    @Transactional
    @Override
    public Boolean update(SearchConfigUpdateReq searchConfigUpdateReq) {
        Long id = searchConfigUpdateReq.getId();
        if (Objects.isNull(id)) {
            throw new ApplicationException(ErrCodeEnum.ID_IS_NULL_ERROR);
        }
        checkModelPermissions(searchConfigUpdateReq.getConfigJson());
        Integer isDefault = searchConfigUpdateReq.getIsDefault();
        if (ConfigDefaultEnums.YES.getCode().equals(isDefault))
            setDefault(id);
        Boolean res = searchConfigDomainService.update(BeanUtil.copyProperties(searchConfigUpdateReq, Config.class));
        return res;
    }

    private void checkModelPermissions(String config) {
        if (!StringUtils.hasText(config))
            return;
        JSONObject configJson = JSONObject.parseObject(config);
        String modelName = configJson.getString(MODEL_NAME);
        String planNodelName = configJson.getString(PLAN_MODEL_NAME);
        String rerankModelName = configJson.getString(RERANK_MODEL_NAME);
        String recommendModelName = configJson.getString(RECOMMEND_MODEL_NAME);
        modelClient.getSimpByModeName(modelName);
        modelClient.getSimpByModeName(planNodelName);
        modelClient.getSimpByModeName(rerankModelName);
        modelClient.getSimpByModeName(recommendModelName);
    }

    @Override
    public Boolean updateStatus(Long configId, Integer status) {
        if (Objects.isNull(configId)) {
            throw new ApplicationException(ErrCodeEnum.ID_IS_NULL_ERROR);
        }
        if (Objects.isNull(status) || ConfigStatusEnums.ENABLED.getCode() != status || ConfigStatusEnums.DISABLE.getCode() != status) {
            throw new ApplicationException(ErrCodeEnum.CONFIG_STATUS_ERROR);
        }
        return searchConfigDomainService.updateStatus(configId, status);
    }

    @Override
    public Boolean deleteById(Long configId) {
        if (Objects.isNull(configId)) {
            throw new ApplicationException(ErrCodeEnum.ID_IS_NULL_ERROR);
        }
        return searchConfigDomainService.deleteById(configId);
    }

    @Override
    public Config getConfigById(Long configId) {
        return searchConfigDomainService.getConfigById(configId);
    }

    @Override
    public Boolean setDefault(Long configId) {
        if (Objects.isNull(configId)) {
            throw new ApplicationException(ErrCodeEnum.ID_IS_NULL_ERROR);
        }
        Config defaultConfig = searchConfigDomainService.getDefaultConfig();
        if (!Objects.isNull(defaultConfig))
            searchConfigDomainService.updateDefault(defaultConfig.getId(), ConfigDefaultEnums.NO.getCode());
        return searchConfigDomainService.updateDefault(configId, ConfigDefaultEnums.YES.getCode());
    }

    @Override
    public Page<SearchConfigDTO> searchList(SearchConfigQueryReq searchConfigQueryReq) {
        Page<SearchConfigDTO> page = getConfList(null, searchConfigQueryReq, SearchConfigScopeEnums.OWN);
        page.getRecords().forEach(searchConfigDTO -> {
            searchConfigDTO.setPermission(PermissionEnums.ALL.getCode());
        });
        return page;
    }

    @Override
    public Page<SearchConfigDTO> searchAllList(SearchConfigQueryReq searchConfigQueryReq) {
        List<PrivilegeDTO> privilegeDTOList = authClient.getAllPermission(PrivilegeTypeEnums.INDEX_CONF.getCode(), null);
        Map<Long, PrivilegeDTO> permissionMap = privilegeDTOList.stream().collect(Collectors.toMap(PrivilegeDTO::getTargetId, Function.identity(), (v1, v2) -> v1));

        if (!CollectionUtils.isEmpty(permissionMap)) {
            return getConfList(new ArrayList<>(permissionMap.keySet()), searchConfigQueryReq, SearchConfigScopeEnums.ALL);
        }
        return getConfList(null, searchConfigQueryReq, SearchConfigScopeEnums.OWN);
    }

    @Override
    public Page<SearchConfigDTO> shareList(SearchConfigQueryReq searchConfigQueryReq) {
        List<PrivilegeDTO> privilegeDTOList = authClient.getAllPermission(PrivilegeTypeEnums.INDEX_CONF.getCode(), null);
        if (CollUtil.isEmpty(privilegeDTOList))
            return new Page<>();
        Map<Long, PrivilegeDTO> permissionMap = privilegeDTOList.stream().collect(Collectors.toMap(PrivilegeDTO::getTargetId, Function.identity(), (v1, v2) -> v1));

        Page<SearchConfigDTO> page = getConfList(new ArrayList<>(permissionMap.keySet()), searchConfigQueryReq, SearchConfigScopeEnums.SHARE);
        page.getRecords().forEach(searchConfigDTO -> {
            PrivilegeDTO privilegeDTO = permissionMap.get(searchConfigDTO.getId());
            searchConfigDTO.setPermission(Objects.isNull(privilegeDTO) ? null : privilegeDTO.getPermission());
        });
        return page;
    }

    private Page<SearchConfigDTO> getConfList(List<Long> confIds, SearchConfigQueryReq searchConfigQueryReq, SearchConfigScopeEnums scope) {
        String fuzzy = searchConfigQueryReq.getFuzzy();
        Long pageNo = searchConfigQueryReq.getPageNo();
        Long pageSize = searchConfigQueryReq.getPageSize();
        Page<Config> searchConfigPage = searchConfigDomainService.list(confIds, fuzzy, pageNo, pageSize, scope);
        Page<SearchConfigDTO> result = BeanUtil.copyProperties(searchConfigPage, Page.class);
        result.setRecords(BeanUtil.copyToList(searchConfigPage.getRecords(), SearchConfigDTO.class));
        if (!CollectionUtils.isEmpty(result.getRecords())) {
            result.getRecords().get(0).setModel(Boolean.TRUE);
        }
        result.setRecords(BeanUtil.copyToList(searchConfigPage.getRecords(), SearchConfigDTO.class));
        return result;
    }

    @Override
    public Set<SearchConfigDTO> helperConfList(String nameOrId) {
        //用户创建的配置 + 授予用户的配置 + 授予用户所属机构组的配置;
        // 1. 用户创建的配置
        Page<Config> userPage = searchConfigDomainService.list(null, nameOrId, 1L, Long.MAX_VALUE, SearchConfigScopeEnums.OWN);
        List<Config> userConfigList = userPage.getRecords();
        // 2. 共享给用户的配置
        List<PrivilegeDTO> privilegeDTOList = authClient.getAllPermission(PrivilegeTypeEnums.INDEX_CONF.getCode(), null);
        Map<Long, PrivilegeDTO> permissionMap = privilegeDTOList.stream().collect(Collectors.toMap(PrivilegeDTO::getTargetId, Function.identity(), (v1, v2) -> v1));

        if (!CollectionUtils.isEmpty(permissionMap)) {
            Page<Config> permissionPage = searchConfigDomainService.list(new ArrayList<>(permissionMap.keySet()), nameOrId, 1L, Long.MAX_VALUE, SearchConfigScopeEnums.SHARE);
            List<Config> permissionConfigList = permissionPage.getRecords();
            if (!CollectionUtils.isEmpty(permissionConfigList))
                userConfigList.addAll(permissionConfigList);
        }
        //数据去重
        return new HashSet<>(BeanUtil.copyToList(userConfigList, SearchConfigDTO.class));
    }

    @Override
    public int updateSensitiveWord(Long wordId) {
        return searchConfigDomainService.updateSensitiveWord(wordId);
    }

    @Override
    public int updateKnowledgeBase(String baseName, String sourceName) {
        searchConfigDomainService.updateKnowledgeBase(baseName);
        return searchConfigDomainService.updateSourceKnowledgeBase(sourceName);
    }

    @Override
    public Boolean updateTrace(String modelName, Boolean needTrace) {
        if (!StringUtils.hasText(modelName) || Objects.isNull(needTrace))
            return false;
        return searchConfigDomainService.updateTrace(modelName, needTrace);
    }

    @Override
    public Boolean updateModelConfig(String modelName, Boolean thinking) {
        return searchConfigDomainService.updateModelConfig(modelName, thinking);
    }

    @Override
    public int updateKbSourceName(String sourceName, String targetName) {
        return searchConfigDomainService.updateKbSourceName(sourceName, targetName);
    }

    @Override
    public int updateDbIndex(String dbIndex) {
        return searchConfigDomainService.updateDbIndex(dbIndex);
    }

    @Override
    public int renameDbIndex(String dbIndex, String newDbLabel, String oldDbLabel) {
        return searchConfigDomainService.renameDbIndex(dbIndex, newDbLabel, oldDbLabel);
    }

    @Override
    public String queryCreator(Long id) {
        Config config = searchConfigDomainService.getConfigById(id);
        return Objects.isNull(config) ? null : config.getCreateBy();
    }

    @Override
    public Boolean transferProperty(String owner, String receiver, boolean isClearKb) {
        return searchConfigDomainService.transferProperty(owner, receiver, isClearKb);
    }

    @Override
    public Object configItemLimit() {
        if (!StringUtils.hasText(searchConfigLimit))
            return null;
        return JSON.parseObject(searchConfigLimit);
    }

    @Override
    public SearchConfigDTO getById(Long configId) {
        Config config = searchConfigDomainService.getConfigById(configId);
        return Objects.isNull(config) ? null : BeanUtil.copyProperties(config, SearchConfigDTO.class);
    }

    @Override
    public Boolean checkName(Long configId, String configName) {
        User user = UserContext.getUser();
        String userName = user.getUserName();
        Config config = searchConfigDomainService.getConfigByName(userName, configName);
        if (Objects.isNull(config))
            return false;
        return !config.getId().equals(configId);
    }

    @Override
    public Boolean replaceModel(String sourceModelName, String targetModelName) {
        return searchConfigDomainService.replaceModel(sourceModelName, targetModelName);
    }

    //    @Override
//    public List<RerankDTO> getReranks() {
//        return JSON.parseArray(searchConfigRerank, RerankDTO.class);
//    }

    @Override
    public int selectReferenceByModelName(String modelName) {
        return searchConfigDomainService.selectReferenceByModelName(modelName);
    }
}
