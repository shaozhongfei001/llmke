package com.gientech.ragauthservice.domain.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragauthservice.domain.entity.ResourceInterface;
import com.gientech.ragcommon.auth.dto.ResourceInterfaceDTO;

import java.util.List;

public interface ResourceInterfaceDomainService {

    ResourceInterface findById(Long id);

    Boolean save(ResourceInterface resourceInterface);

    Boolean updateById(ResourceInterface resourceInterface);

    Page<ResourceInterface> list(Long pageNo, Long pageSize);

    Boolean deleteById(Long id);

    List<ResourceInterface> findByResourceIds(List<Long> resourceIds);
}
