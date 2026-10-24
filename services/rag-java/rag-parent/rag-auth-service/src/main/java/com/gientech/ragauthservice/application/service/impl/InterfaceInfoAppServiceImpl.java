package com.gientech.ragauthservice.application.service.impl;

import cn.hutool.core.bean.BeanUtil;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.plugins.pagination.PageDTO;
import com.gientech.ragauthservice.application.service.InterfaceInfoAppService;
import com.gientech.ragauthservice.domain.entity.InterfaceInfo;
import com.gientech.ragauthservice.domain.service.InterfaceInfoDomainService;
import com.gientech.ragcommon.auth.dto.InterfaceInfoDTO;
import com.gientech.ragcommon.auth.request.SaveInterfaceInfoReq;
import com.gientech.ragcommon.auth.request.UpdateInterfaceInfoReq;
import com.google.common.collect.Lists;
import com.google.common.collect.Maps;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;

import java.util.List;
import java.util.Map;
import java.util.Objects;

@Service
public class InterfaceInfoAppServiceImpl implements InterfaceInfoAppService {

    @Autowired
    private InterfaceInfoDomainService interfaceInfoDomainService;

    @Override
    public InterfaceInfoDTO findById(Long id) {
        if (Objects.isNull(id))
            return null;
        InterfaceInfo byId = interfaceInfoDomainService.findById(id);
        return BeanUtil.copyProperties(byId, InterfaceInfoDTO.class);
    }

    @Override
    public Boolean save(SaveInterfaceInfoReq interfaceInfoReq) {
        if (Objects.isNull(interfaceInfoReq))
            return false;
        return interfaceInfoDomainService.save(BeanUtil.copyProperties(interfaceInfoReq, InterfaceInfo.class));
    }

    @Override
    public Boolean updateById(UpdateInterfaceInfoReq interfaceInfoReq) {
        if (Objects.isNull(interfaceInfoReq))
            return false;
        return interfaceInfoDomainService.updateById(BeanUtil.copyProperties(interfaceInfoReq, InterfaceInfo.class));
    }

    @Override
    public Page<InterfaceInfoDTO> list(Long pageNo, Long pageSize) {
        pageNo = Objects.isNull(pageNo) ? 1 : pageNo;
        pageSize = Objects.isNull(pageSize) ? 10 : pageSize;
        Page<InterfaceInfo> page = interfaceInfoDomainService.list(pageNo, pageSize);
        Page<InterfaceInfoDTO> result = new PageDTO<>();
        BeanUtil.copyProperties(page, result);
        result.setRecords(BeanUtil.copyToList(page.getRecords(), InterfaceInfoDTO.class));
        return result;
    }

    @Override
    public Page<InterfaceInfoDTO> listExtInterfaces(Long pageNo, Long pageSize, String fuzzy) {
        pageNo = Objects.isNull(pageNo) ? 1 : pageNo;
        pageSize = Objects.isNull(pageSize) ? 10 : pageSize;
        Page<InterfaceInfo> page = interfaceInfoDomainService.listExtInterfaces(pageNo, pageSize, fuzzy);
        Page<InterfaceInfoDTO> result = new PageDTO<>();
        BeanUtil.copyProperties(page, result);
        result.setRecords(BeanUtil.copyToList(page.getRecords(), InterfaceInfoDTO.class));
        return result;
    }

    @Override
    public Boolean deleteById(Long id) {
        if (Objects.isNull(id))
            return false;
        return interfaceInfoDomainService.deleteById(id);
    }

    @Override
    public Boolean saveBatch(List<SaveInterfaceInfoReq> infoReqs) {
        if (CollectionUtils.isEmpty(infoReqs))
            return false;
        SaveInterfaceInfoReq interfaceInfo = infoReqs.get(0);
        //删除
//        if (interfaceInfoDomainService.deleteByAppName(interfaceInfo.getAppName())) {
        List<InterfaceInfo> dbInterfaceInfos = interfaceInfoDomainService.findByAppName(interfaceInfo.getAppName());
        Map<String, InterfaceInfo> dbInterfaceInfoMap = convertToMap(dbInterfaceInfos);

        List<InterfaceInfo> needToInserts = Lists.newArrayList();

        infoReqs.forEach(infoReq -> {
            String appName = infoReq.getAppName();
            String url = infoReq.getUrl();
            String method = infoReq.getMethod();
            InterfaceInfo dbInterfaceInfo = dbInterfaceInfoMap.get(appName + ":" + url + ":" + method);
            if (Objects.isNull(dbInterfaceInfo))
                needToInserts.add(BeanUtil.copyProperties(infoReq, InterfaceInfo.class));
        });

        if (!CollectionUtils.isEmpty(needToInserts))
            interfaceInfoDomainService.saveBatch(needToInserts);
        return true;
//        }

//        return false;
    }

    private Map<String, InterfaceInfo> convertToMap(List<InterfaceInfo> dbInterfaceInfos) {
        Map<String, InterfaceInfo> dbInterfaceInfoMap = Maps.newHashMap();
        if (CollectionUtils.isEmpty(dbInterfaceInfos))
            return dbInterfaceInfoMap;
        dbInterfaceInfos.forEach(interfaceInfo -> {
            String appName = interfaceInfo.getAppName();
            String url = interfaceInfo.getUrl();
            String method = interfaceInfo.getMethod();
            dbInterfaceInfoMap.put(appName + ":" + url + ":" + method, interfaceInfo);
        });
        return dbInterfaceInfoMap;
    }
}
