package com.gientech.ragqaservice.domain.repository;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.qa.request.ApiKeyQueryReq;
import com.gientech.ragqaservice.domain.entity.ApiKeyInfo;

public interface ApiKeyInfoRepository {

   ApiKeyInfo findById(Long id);

    Boolean save(ApiKeyInfo apiKeyInfo);

    Boolean updateById(ApiKeyInfo apiKeyInfo);

    Page<ApiKeyInfo> list(ApiKeyQueryReq apiKeyQueryReq);

    Boolean deleteById(Long id);

    ApiKeyInfo getByApiKey(String apiKey);
}
