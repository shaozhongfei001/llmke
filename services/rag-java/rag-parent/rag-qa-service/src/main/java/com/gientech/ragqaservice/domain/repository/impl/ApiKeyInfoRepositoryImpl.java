package com.gientech.ragqaservice.domain.repository.impl;

import cn.hutool.core.bean.BeanUtil;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragcommon.index.enmus.IsDelEnums;
import com.gientech.ragcommon.qa.enmus.ApiKeyStatusEnums;
import com.gientech.ragcommon.qa.enmus.ConfigIsDelEnums;
import com.gientech.ragcommon.qa.request.ApiKeyQueryReq;
import com.gientech.ragqaservice.domain.entity.ApiKeyInfo;
import com.gientech.ragqaservice.domain.mapper.ApiKeyInfoMapper;
import com.gientech.ragqaservice.domain.model.ApiKeyInfoDO;
import com.gientech.ragqaservice.domain.model.SearchConfigDO;
import com.gientech.ragqaservice.domain.repository.ApiKeyInfoRepository;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;
import java.util.Date;
import java.util.List;
import java.util.Objects;

@Repository
public class  ApiKeyInfoRepositoryImpl implements  ApiKeyInfoRepository {

    @Autowired
    private  ApiKeyInfoMapper  apiKeyInfoMapper;

    @Override
    public ApiKeyInfo findById(Long id) {
        QueryWrapper<ApiKeyInfoDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.lambda().eq(ApiKeyInfoDO::getIsDel, IsDelEnums.NORMAL.getCode())
                .eq(ApiKeyInfoDO::getId, id).last("limit 1");
        ApiKeyInfoDO apiKeyInfoDO =  apiKeyInfoMapper.selectOne(queryWrapper);
        return Objects.isNull(apiKeyInfoDO) ? null : BeanUtil.copyProperties(apiKeyInfoDO,ApiKeyInfo.class);
    }

    @Override
    public Boolean save(ApiKeyInfo apiKeyInfo) {
        User user = UserContext.getUser();
        String userName = user.getUserName();
        apiKeyInfo.setModifyBy(userName);
        apiKeyInfo.setCreateBy(userName);
        apiKeyInfo.setGmtCreate(new Date());
        apiKeyInfo.setGmtModified(apiKeyInfo.getGmtCreate());
        return apiKeyInfoMapper.insert(BeanUtil.copyProperties(apiKeyInfo, ApiKeyInfoDO.class)) > 0;
    }

    @Override
    public Boolean updateById(ApiKeyInfo apiKeyInfo) {
        if (Objects.isNull(apiKeyInfo.getId()))
            return false;
        User user = UserContext.getUser();
        String userName = user.getUserName();
        apiKeyInfo.setModifyBy(userName);
        apiKeyInfo.setGmtModified(new Date());
        return apiKeyInfoMapper.updateById(BeanUtil.copyProperties(apiKeyInfo, ApiKeyInfoDO.class)) > 0;
    }

    @Override
    public Page<ApiKeyInfo> list(ApiKeyQueryReq apiKeyQueryReq) {
        Long pageNo = apiKeyQueryReq.getPageNo();
        Long pageSize = apiKeyQueryReq.getPageSize();
        Integer status = apiKeyQueryReq.getStatus();
        String fuzzy = apiKeyQueryReq.getFuzzy();
        Integer bizType = apiKeyQueryReq.getBizType();
        Long targetId = apiKeyQueryReq.getTargetId();

        QueryWrapper<ApiKeyInfoDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.lambda().eq(!Objects.isNull(status),ApiKeyInfoDO::getStatus, status)
                .eq(ApiKeyInfoDO::getTargetId, targetId)
                .eq(ApiKeyInfoDO::getIsDel, IsDelEnums.NORMAL.getCode())
                .eq(!Objects.isNull(bizType),ApiKeyInfoDO::getBizType,bizType)
                .orderByDesc(ApiKeyInfoDO::getGmtCreate);

        if (StringUtils.isNotBlank(fuzzy)) {
            queryWrapper.and(name -> name
                    .like("api_key", fuzzy)
                    .or(id -> id.like("id", fuzzy)));
        }

        Page<ApiKeyInfoDO> page = new Page<>(pageNo, pageSize);
        Page<ApiKeyInfoDO> pageResult = apiKeyInfoMapper.selectPage(page, queryWrapper);
        Page<ApiKeyInfo> listPage = new Page<>();
        BeanUtil.copyProperties(pageResult,listPage);
        listPage.setRecords(BeanUtil.copyToList(pageResult.getRecords(),ApiKeyInfo.class));
        return listPage;
    }

    @Override
    public Boolean deleteById(Long id) {
        if (Objects.isNull(id)) {
            return false;
        }
        ApiKeyInfoDO apiKeyInfoDO = new ApiKeyInfoDO();
        apiKeyInfoDO.setId(id);
        apiKeyInfoDO.setIsDel(ConfigIsDelEnums.YES.getCode());
        return apiKeyInfoMapper.updateById(apiKeyInfoDO) > 0;
    }

    @Override
    public ApiKeyInfo getByApiKey(String apiKey) {
        QueryWrapper<ApiKeyInfoDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.lambda().eq(ApiKeyInfoDO::getIsDel, IsDelEnums.NORMAL.getCode())
                .eq(ApiKeyInfoDO::getApiKey, apiKey).last("limit 1");
        ApiKeyInfoDO apiKeyInfoDO =  apiKeyInfoMapper.selectOne(queryWrapper);
        return Objects.isNull(apiKeyInfoDO) ? null : BeanUtil.copyProperties(apiKeyInfoDO,ApiKeyInfo.class);
    }
}
