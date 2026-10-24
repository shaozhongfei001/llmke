package com.gientech.ragauthservice.domain.service.impl;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragauthservice.domain.entity.ResourceInterface;
import com.gientech.ragauthservice.domain.repository.ResourceInterfaceRepository;
import com.gientech.ragauthservice.domain.service.ResourceInterfaceDomainService;
import com.gientech.ragcommon.auth.dto.ResourceInterfaceDTO;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class ResourceInterfaceDomainServiceImpl implements ResourceInterfaceDomainService {

    @Autowired
    private ResourceInterfaceRepository resourceInterfaceRepository;

    @Override
    public ResourceInterface findById(Long id) {
        return resourceInterfaceRepository.findById(id);
    }

    @Override
    public Boolean save(ResourceInterface resourceInterface) {
        return resourceInterfaceRepository.save(resourceInterface);
    }

    @Override
    public Boolean updateById(ResourceInterface resourceInterface) {
        return resourceInterfaceRepository.updateById(resourceInterface);
    }

    @Override
    public Page<ResourceInterface> list(Long pageNo, Long pageSize) {
        return resourceInterfaceRepository.list(pageNo,pageSize);
    }

    @Override
    public Boolean deleteById(Long id) {
         return resourceInterfaceRepository.deleteById(id);
    }

    @Override
    public List<ResourceInterface> findByResourceIds(List<Long> resourceIds) {
        return resourceInterfaceRepository.findByResourceIds(resourceIds);
    }
}
