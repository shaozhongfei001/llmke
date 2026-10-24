package com.gientech.ragauthservice.application.service.impl;

import cn.hutool.core.bean.BeanUtil;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.plugins.pagination.PageDTO;
import com.gientech.ragauthservice.application.service.ResourceInterfaceAppService;
import com.gientech.ragauthservice.domain.entity.ResourceInterface;
import com.gientech.ragauthservice.domain.service.ResourceInterfaceDomainService;
import com.gientech.ragcommon.auth.dto.ResourceInterfaceDTO;
import com.gientech.ragcommon.auth.request.SaveResourceInterfaceReq;
import com.gientech.ragcommon.auth.request.UpdateResourceInterfaceReq;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import java.util.Objects;

@Service
public class ResourceInterfaceAppServiceImpl implements ResourceInterfaceAppService {

    @Autowired
    private ResourceInterfaceDomainService resourceInterfaceDomainService;

    @Override
    public ResourceInterfaceDTO findById(Long id) {
        if(Objects.isNull(id))
            return null;
        ResourceInterface byId = resourceInterfaceDomainService.findById(id);
        return BeanUtil.copyProperties(byId,ResourceInterfaceDTO.class);
    }

    @Override
    public Boolean save(SaveResourceInterfaceReq resourceInterfaceReq) {
        if(Objects.isNull(resourceInterfaceReq))
            return false;
       return resourceInterfaceDomainService.save(BeanUtil.copyProperties(resourceInterfaceReq,ResourceInterface.class));
    }

    @Override
    public Boolean updateById(UpdateResourceInterfaceReq resourceInterfaceReq) {
        if(Objects.isNull(resourceInterfaceReq))
            return false;
        return resourceInterfaceDomainService.updateById(BeanUtil.copyProperties(resourceInterfaceReq,ResourceInterface.class));
    }

    @Override
    public Page<ResourceInterfaceDTO> list(Long pageNo, Long pageSize) {
        pageNo = Objects.isNull(pageNo) ? 1 : pageNo;
        pageSize = Objects.isNull(pageSize) ? 10 : pageSize;
        Page<ResourceInterface> page = resourceInterfaceDomainService.list(pageNo, pageSize);
        Page<ResourceInterfaceDTO> result = new PageDTO<>();
        BeanUtil.copyProperties(page,result);
        result.setRecords(BeanUtil.copyToList(page.getRecords(),ResourceInterfaceDTO.class));
        return result;
    }

    @Override
    public Boolean deleteById(Long id) {
        if(Objects.isNull(id))
            return false;
        return resourceInterfaceDomainService.deleteById(id);
    }
}
