package com.gientech.ragqaservice.domain.repository.impl;

import cn.hutool.core.bean.BeanUtil;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragcommon.index.enmus.SearchConfigScopeEnums;
import com.gientech.ragcommon.qa.enmus.ConfigIsDelEnums;
import com.gientech.ragcommon.qa.enmus.ConfigStatusEnums;
import com.gientech.ragcommon.qa.entity.Config;
import com.gientech.ragqaservice.domain.mapper.SearchConfigMapper;
import com.gientech.ragqaservice.domain.model.SearchConfigDO;
import com.gientech.ragqaservice.domain.repository.SearchConfigRepository;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;
import org.springframework.util.CollectionUtils;

import java.util.Date;
import java.util.List;
import java.util.Objects;

@Repository
public class SearchConfigRepositoryImpl implements SearchConfigRepository {

    @Autowired
    private SearchConfigMapper searchConfigMapper;

    @Override
    public List<Config> getConfigByUser() {
        User user = UserContext.getUser();
        String userName = user.getUserName();
        QueryWrapper<SearchConfigDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("create_by", userName);
        queryWrapper.eq("is_del", ConfigIsDelEnums.NO.getCode());
        queryWrapper.orderByDesc("gmt_create");
        List<SearchConfigDO> searchConfigDOS = searchConfigMapper.selectList(queryWrapper);
        return CollectionUtils.isEmpty(searchConfigDOS) ? null : BeanUtil.copyToList(searchConfigDOS, Config.class);
    }

    @Override
    public Config getDefaultConfig(int status) {
        User user = UserContext.getUser();
        String userName = user.getUserName();
        QueryWrapper<SearchConfigDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("create_by", userName);
        queryWrapper.eq("is_default", status);
        queryWrapper.eq("is_del", ConfigIsDelEnums.NO.getCode());
        queryWrapper.last("limit 1");
        SearchConfigDO searchConfigDOS = searchConfigMapper.selectOne(queryWrapper);
        return Objects.isNull(searchConfigDOS) ? null : BeanUtil.copyProperties(searchConfigDOS, Config.class);
    }

    @Override
    public Boolean updateStatus(Long id, int status) {
        User user = UserContext.getUser();
        String userName = user.getUserName();

        SearchConfigDO searchConfigDO = new SearchConfigDO();
        searchConfigDO.setId(id);
        searchConfigDO.setStatus(status);
        searchConfigDO.setModifyBy(userName);
        searchConfigDO.setGmtModified(new Date());
        return searchConfigMapper.updateById(searchConfigDO) > 0;
    }

    @Override
    public Config insert(Config config) {
        User user = UserContext.getUser();
        String userName = user.getUserName();
        config.setCreateBy(userName);
        config.setGmtCreate(new Date());
        config.setModifyBy(userName);
        config.setGmtModified(config.getGmtCreate());
        SearchConfigDO searchConfigDO = BeanUtil.copyProperties(config, SearchConfigDO.class);
        searchConfigMapper.insert(searchConfigDO);
        return BeanUtil.copyProperties(searchConfigDO, Config.class);
    }

    @Override
    public Boolean update(Config config) {
        User user = UserContext.getUser();
        String userName = user.getUserName();
        config.setModifyBy(userName);
        config.setGmtModified(config.getGmtCreate());
        SearchConfigDO searchConfigDO = BeanUtil.copyProperties(config, SearchConfigDO.class);
        return searchConfigMapper.updateById(searchConfigDO) > 0;
    }

    @Override
    public Boolean deleteById(Long configId) {
        if (Objects.isNull(configId)) {
            return false;
        }
        SearchConfigDO configDO = new SearchConfigDO();
        configDO.setId(configId);
        configDO.setIsDel(ConfigIsDelEnums.YES.getCode());
        return searchConfigMapper.updateById(configDO) > 0;
    }

    @Override
    public Page<Config> list(List<Long> ids, String fuzzy, Long pageNo, Long pageSize, SearchConfigScopeEnums scope) {

        QueryWrapper<SearchConfigDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("is_del", ConfigIsDelEnums.NO.getCode());

        buildQueryByScope(ids, scope, queryWrapper);

        if (StringUtils.isNotBlank(fuzzy)) {
            queryWrapper.and(name -> name
                    .like("name", fuzzy)
                    .or(id -> id.like("id", fuzzy)));
        }
        queryWrapper.orderByDesc("is_default", "gmt_create");
        Page<SearchConfigDO> page = new Page<>(pageNo, pageSize);
        Page<SearchConfigDO> pageResult = searchConfigMapper.selectPage(page, queryWrapper);
        Page<Config> knowledgeBaseListPage = new Page<>();
        BeanUtil.copyProperties(pageResult, knowledgeBaseListPage);
        knowledgeBaseListPage.setRecords(BeanUtil.copyToList(pageResult.getRecords(), Config.class));
        return knowledgeBaseListPage;
    }

    private void buildQueryByScope(List<Long> ids, SearchConfigScopeEnums scope, QueryWrapper<SearchConfigDO> queryWrapper) {
        User user = UserContext.getUser();
        String userName = user.getUserName();
        switch (scope) {
            case ALL:
                if (!CollectionUtils.isEmpty(ids)) {
                    queryWrapper.nested(wrapper -> wrapper.in("id", ids).or().eq("create_by", userName));
                } else {
                    queryWrapper.eq("create_by", userName);
                }
                break;
            case OWN:
                if (!CollectionUtils.isEmpty(ids)) {
                    queryWrapper.in("id", ids);
                } else {
                    queryWrapper.eq("create_by", userName);
                }
                break;
            case SHARE:
                if (!CollectionUtils.isEmpty(ids)) {
                    queryWrapper.in("id", ids);
                    queryWrapper.ne("create_by", userName);
                }
                break;
            default:
                throw new IllegalArgumentException("Unsupported scope: " + scope);

        }
    }

    @Override
    public Boolean updateDefault(Long id, int defaultCode) {
        if (Objects.isNull(id)) {
            return false;
        }
        SearchConfigDO searchConfigDO = new SearchConfigDO();
        User user = UserContext.getUser();
        searchConfigDO.setId(id);
        searchConfigDO.setIsDefault(defaultCode);
        String userName = user.getUserName();
        searchConfigDO.setModifyBy(userName);
        searchConfigDO.setGmtModified(searchConfigDO.getGmtCreate());
        return searchConfigMapper.updateById(searchConfigDO) > 0;
    }

    @Override
    public Config getById(Long id) {
        QueryWrapper<SearchConfigDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("id", id)
                .eq("is_del", ConfigIsDelEnums.NO.getCode())
                .last("limit 1");
        SearchConfigDO searchConfigDO = searchConfigMapper.selectOne(queryWrapper);
        return Objects.isNull(searchConfigDO) ? null : BeanUtil.copyProperties(searchConfigDO, Config.class);
    }


    @Override
    public Config getConfigById(Long id) {
        if (Objects.isNull(id)) {
            return null;
        }
        QueryWrapper<SearchConfigDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("id", id)
                .eq("status", ConfigStatusEnums.ENABLED.getCode())
                .eq("is_del", ConfigIsDelEnums.NO.getCode())
                .last("limit 1");
        SearchConfigDO searchConfigDO = searchConfigMapper.selectOne(queryWrapper);
        return Objects.isNull(searchConfigDO) ? null : BeanUtil.copyProperties(searchConfigDO, Config.class);
    }

    @Override
    public int updateSensitiveWords(Long wordId) {
        return searchConfigMapper.updateSensitiveWord(String.valueOf(wordId));
    }

    @Override
    public int updateKnowledgeBase(String baseName) {
        return searchConfigMapper.updateKnowledgeBase(baseName);
    }

    @Override
    public int updateSourceKnowledgeBase(String sourceName) {
        return searchConfigMapper.updateSourceKnowledgeBase(sourceName);
    }

    @Override
    public int updateDbIndex(String dbIndex) {
        return searchConfigMapper.updateDbIndex(dbIndex);
    }

    @Override
    public int renameDbIndex(String dbIndex, String newDbLabel, String oldDbLabel) {
        return searchConfigMapper.renameDbIndex(dbIndex, newDbLabel, oldDbLabel);
    }

    @Override
    public int updateKbSourceName(String sourceName, String targetName) {
        return searchConfigMapper.updateKbSourceName(sourceName, targetName);
    }

    @Override
    public Boolean updateTrace(String modelName, Boolean needTrace) {
        return searchConfigMapper.updateTrace(modelName, needTrace) > 0;
    }

    @Override
    public Boolean updateModelConfig(String modelName, Boolean thinking) {
        return searchConfigMapper.updateModelConfig(modelName, thinking) > 0;
    }

    @Override
    public int transferProperty(String owner, String receiver, boolean isClearKb) {
        QueryWrapper<SearchConfigDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("create_by", owner).eq("is_del", ConfigIsDelEnums.NO.getCode());
        List<SearchConfigDO> searchConfigDOS = searchConfigMapper.selectList(queryWrapper);
        if (!CollectionUtils.isEmpty(searchConfigDOS)) {
            List<Long> ids = searchConfigDOS.stream().map(SearchConfigDO::getId).toList();
            return searchConfigMapper.updateCreator(ids, receiver, isClearKb);
        }
        return 0;
    }

    @Override
    public Config getConfigByName(String userName, String configName) {
        QueryWrapper<SearchConfigDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("name", configName)
                .eq(StringUtils.isNotBlank(userName), "create_by", userName)
                .eq("is_del", ConfigIsDelEnums.NO.getCode())
                .last("limit 1");
        SearchConfigDO searchConfigDO = searchConfigMapper.selectOne(queryWrapper);
        return Objects.isNull(searchConfigDO) ? null : BeanUtil.copyProperties(searchConfigDO, Config.class);
    }

    @Override
    public Boolean replaceModel(String sourceModelName, String targetModelName) {
        return searchConfigMapper.replaceModelName(sourceModelName, targetModelName) > 0;
    }

    @Override
    public int selectReferenceByModelName(String modelName) {
        return searchConfigMapper.selectReferenceByModelName(modelName);
    }
}