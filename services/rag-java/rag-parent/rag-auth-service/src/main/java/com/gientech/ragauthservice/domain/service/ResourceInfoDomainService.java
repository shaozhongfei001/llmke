package com.gientech.ragauthservice.domain.service;


import com.gientech.ragauthservice.domain.entity.ResourceInfo;
import com.gientech.ragcommon.auth.dto.MenuDTO;

import java.util.List;

/**
 * <p>
 * 资源表 服务类
 * </p>
 *
 * @author wudf
 * @since 2024-06-26
 */
public interface ResourceInfoDomainService{

    List<ResourceInfo> queryByRoleIds(List<Long> roleIds);

    List<ResourceInfo> queryVisibleByRoleIds(List<Long> roleIds);

    ResourceInfo queryByPidAndUrl(Long pid,String url);

    Boolean addResource(ResourceInfo resourceInfo);

    Boolean deleteResource(Long resourceId);

    Boolean updateResource(ResourceInfo resourceInfo);

    List<MenuDTO> getMenusByRoleIds(List<Long> roleIds);

    List<ResourceInfo> listOperResources();
}
