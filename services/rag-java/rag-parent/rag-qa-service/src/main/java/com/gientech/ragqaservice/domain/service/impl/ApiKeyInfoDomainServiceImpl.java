package com.gientech.ragqaservice.domain.service.impl;

import com.alibaba.fastjson2.JSON;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.qa.constant.QaConstant;
import com.gientech.ragcommon.qa.request.ApiKeyQueryReq;
import com.gientech.ragqaservice.domain.entity.ApiKeyInfo;
import com.gientech.ragqaservice.domain.repository.ApiKeyInfoRepository;
import com.gientech.ragqaservice.domain.service.ApiKeyInfoDomainService;
import com.google.common.collect.Maps;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.*;

@Service
public class ApiKeyInfoDomainServiceImpl implements ApiKeyInfoDomainService {

    @Autowired
    private ApiKeyInfoRepository apiKeyInfoRepository;

    @Override
    public ApiKeyInfo findById(Long id) {
        return apiKeyInfoRepository.findById(id);
    }

    @Override
    public Boolean save(ApiKeyInfo apiKeyInfo) {
        return apiKeyInfoRepository.save(apiKeyInfo);
    }

    @Override
    public Boolean updateById(ApiKeyInfo apiKeyInfo) {
        return apiKeyInfoRepository.updateById(apiKeyInfo);
    }

    @Override
    public Page<ApiKeyInfo> list(ApiKeyQueryReq apiKeyQueryReq) {
        return apiKeyInfoRepository.list(apiKeyQueryReq);
    }

    @Override
    public Boolean deleteById(Long id) {
         return apiKeyInfoRepository.deleteById(id);
    }

    @Override
    public ApiKeyInfo getByApiKey(String apiKey) {
        return apiKeyInfoRepository.getByApiKey(apiKey);
    }

    @Override
    public Boolean checkApiKey(String apiKey) {
        if(StringUtils.isEmpty(apiKey))
            return false;
        ApiKeyInfo apiKeyInfo = this.getByApiKey(apiKey);
        if(Objects.isNull(apiKeyInfo))
            return false;
        Date expireTime = apiKeyInfo.getExpireTime();
        return new Date().before(expireTime);
    }
}
