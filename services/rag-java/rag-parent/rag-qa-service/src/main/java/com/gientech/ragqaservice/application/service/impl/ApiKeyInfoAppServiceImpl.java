package com.gientech.ragqaservice.application.service.impl;

import cn.hutool.core.bean.BeanUtil;
import com.alibaba.fastjson2.JSON;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.plugins.pagination.PageDTO;
import com.gientech.ragcommon.infrastructure.utils.AesEncryptUtil;
import com.gientech.ragcommon.qa.constant.QaConstant;
import com.gientech.ragcommon.qa.request.ApiKeyQueryReq;
import com.gientech.ragqaservice.application.service.ApiKeyInfoAppService;
import com.gientech.ragqaservice.domain.entity.ApiKeyInfo;
import com.gientech.ragqaservice.domain.service.ApiKeyInfoDomainService;
import com.gientech.ragcommon.qa.dto.ApiKeyInfoDTO;
import com.gientech.ragcommon.qa.request.SaveApiKeyInfoReq;
import com.gientech.ragcommon.qa.request.UpdateApiKeyInfoReq;
import com.google.common.collect.Maps;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.Base64;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;

@Service
public class ApiKeyInfoAppServiceImpl implements ApiKeyInfoAppService {

    @Autowired
    private ApiKeyInfoDomainService apiKeyInfoDomainService;

    @Autowired
    private AesEncryptUtil aesEncryptUtil;

    @Override
    public ApiKeyInfoDTO findById(Long id) {
        if(Objects.isNull(id))
            return null;
        ApiKeyInfo byId = apiKeyInfoDomainService.findById(id);
        return BeanUtil.copyProperties(byId,ApiKeyInfoDTO.class);
    }

    @Override
    public Boolean save(SaveApiKeyInfoReq apiKeyInfoReq) {
        if(Objects.isNull(apiKeyInfoReq))
            return false;
        ApiKeyInfo apiKeyInfo = BeanUtil.copyProperties(apiKeyInfoReq, ApiKeyInfo.class);

        Integer targetId = apiKeyInfoReq.getTargetId();
        String uuId = UUID.randomUUID().toString().replace("-", "");

        Map<String,Object> apiKey = Maps.newHashMap();
        apiKey.put(QaConstant.API_KEY,uuId);
        apiKey.put(QaConstant.BIZ_TARGET_ID,targetId);
        apiKeyInfo.setApiKey(QaConstant.API_KEY_PREFIX + aesEncryptUtil.encrypt(JSON.toJSONString(apiKey)));

       return apiKeyInfoDomainService.save(apiKeyInfo);
    }

    @Override
    public Boolean updateById(UpdateApiKeyInfoReq apiKeyInfoReq) {
        if(Objects.isNull(apiKeyInfoReq))
            return false;
        return apiKeyInfoDomainService.updateById(BeanUtil.copyProperties(apiKeyInfoReq,ApiKeyInfo.class));
    }

    @Override
    public Page<ApiKeyInfoDTO> list(ApiKeyQueryReq apiKeyQueryReq) {
        Page<ApiKeyInfo> page = apiKeyInfoDomainService.list(apiKeyQueryReq);
        Page<ApiKeyInfoDTO> result = new PageDTO<>();
        BeanUtil.copyProperties(page,result);
        result.setRecords(BeanUtil.copyToList(page.getRecords(),ApiKeyInfoDTO.class));
        return result;
    }

    @Override
    public Boolean deleteById(Long id) {
        if(Objects.isNull(id))
            return false;
        return apiKeyInfoDomainService.deleteById(id);
    }

    @Override
    public Boolean checkApiKey(String apiKey) {
        return apiKeyInfoDomainService.checkApiKey(apiKey);
    }
}
