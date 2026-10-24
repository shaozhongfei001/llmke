package com.gientech.ragauthservice.domain.repository;

import com.gientech.ragauthservice.domain.entity.ResourceInfo;
import com.gientech.ragauthservice.domain.model.ResourceInfoDO;

import java.util.List;

public interface ResourceInfoRepository {

    List<ResourceInfo> queryByRoleIds(List<Long> roleIds);

    List<ResourceInfo> queryVisibleByRoleIds(List<Long> roleIds);

    ResourceInfo queryByPidAndUrl(Long pid, String url);

    Boolean save(ResourceInfo resourceInfo);

    Boolean deleteById(Long resourceId);

    Boolean updateResource(ResourceInfo resourceInfo);

    List<ResourceInfo> listOperResources();
}
