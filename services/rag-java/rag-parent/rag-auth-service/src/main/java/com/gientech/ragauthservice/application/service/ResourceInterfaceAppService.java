package com.gientech.ragauthservice.application.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragcommon.auth.dto.ResourceInterfaceDTO;
import com.gientech.ragcommon.auth.request.SaveResourceInterfaceReq;
import com.gientech.ragcommon.auth.request.UpdateResourceInterfaceReq;

public interface ResourceInterfaceAppService {

    ResourceInterfaceDTO findById(Long id);

    Boolean save(SaveResourceInterfaceReq resourceInterfaceReq);

    Boolean updateById(UpdateResourceInterfaceReq resourceInterfaceReq);

    Page<ResourceInterfaceDTO> list(Long pageNo, Long pageSize);

    Boolean deleteById(Long id);

}
