package com.gientech.ragauthservice.domain.repository;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragauthservice.domain.entity.InterfaceInfo;

import java.util.List;
import java.util.Map;

public interface InterfaceInfoRepository {

   InterfaceInfo findById(Long id);

    Boolean save(InterfaceInfo interfaceInfo);

    Boolean updateById(InterfaceInfo interfaceInfo);

    Page<InterfaceInfo> list(Long pageNo, Long pageSize);

    Page<InterfaceInfo> listExtInterfaces(Long pageNo, Long pageSize, String fuzzy);

    Boolean deleteById(Long id);

    List<InterfaceInfo> findByAppName(String appName);

   int saveBatch(List<InterfaceInfo> needToInserts);

    Boolean deleteByAppName(String appName);

    List<InterfaceInfo> findByIds(List<Long> resourceIds);
}
