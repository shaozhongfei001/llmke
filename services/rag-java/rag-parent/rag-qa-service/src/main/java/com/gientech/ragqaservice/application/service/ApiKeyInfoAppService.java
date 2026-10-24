package com.gientech.ragqaservice.application.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.qa.dto.ApiKeyInfoDTO;
import com.gientech.ragcommon.qa.request.ApiKeyQueryReq;
import com.gientech.ragcommon.qa.request.SaveApiKeyInfoReq;
import com.gientech.ragcommon.qa.request.UpdateApiKeyInfoReq;

public interface ApiKeyInfoAppService {

    ApiKeyInfoDTO findById(Long id);

    Boolean save(SaveApiKeyInfoReq apiKeyInfoReq);

    Boolean updateById(UpdateApiKeyInfoReq apiKeyInfoReq);

    Page<ApiKeyInfoDTO> list(ApiKeyQueryReq apiKeyQueryReq);

    Boolean deleteById(Long id);

    Boolean checkApiKey(String apiKey);

}
