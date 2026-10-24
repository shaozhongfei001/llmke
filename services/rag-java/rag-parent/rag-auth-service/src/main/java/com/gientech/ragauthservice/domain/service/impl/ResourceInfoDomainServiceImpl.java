package com.gientech.ragauthservice.domain.service.impl;


import com.gientech.ragauthservice.domain.entity.ResourceInfo;
import com.gientech.ragauthservice.domain.repository.ResourceInfoRepository;
import com.gientech.ragauthservice.domain.service.ResourceInfoDomainService;
import com.gientech.ragcommon.auth.dto.MenuDTO;
import com.gientech.ragcommon.auth.enums.ResourceTypeEnum;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;
import org.springframework.util.StringUtils;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.stream.Collectors;


@Service
public class ResourceInfoDomainServiceImpl implements ResourceInfoDomainService {

    @Autowired
    private ResourceInfoRepository resourceInfoRepository;

    @Override
    public List<ResourceInfo> queryByRoleIds(List<Long> roleIds) {
        if(CollectionUtils.isEmpty(roleIds))
            return List.of();
        return resourceInfoRepository.queryByRoleIds(roleIds);
    }

    @Override
    public List<ResourceInfo> queryVisibleByRoleIds(List<Long> roleIds) {
        if(CollectionUtils.isEmpty(roleIds))
            return null;
        return resourceInfoRepository.queryVisibleByRoleIds(roleIds);
    }

    @Override
    public ResourceInfo queryByPidAndUrl(Long pid, String url) {
        if(!StringUtils.hasText(url))
            return null;
        return resourceInfoRepository.queryByPidAndUrl(pid,url);
    }

    @Override
    public Boolean addResource(ResourceInfo resourceInfo) {
        return resourceInfoRepository.save(resourceInfo);
    }

    @Override
    public Boolean deleteResource(Long resourceId) {
        if(resourceId == null)
            return false;
        return resourceInfoRepository.deleteById(resourceId);
    }

    @Override
    public Boolean updateResource(ResourceInfo resourceInfo) {
        return resourceInfoRepository.updateResource(resourceInfo);
    }

    @Override
    public List<MenuDTO> getMenusByRoleIds(List<Long> roleIds) {
        List<ResourceInfo> resourceInfoList = resourceInfoRepository.queryVisibleByRoleIds(roleIds);
        if(CollectionUtils.isEmpty(resourceInfoList)){
            return null;
        }
        return getMenus(resourceInfoList);
    }

    private List<MenuDTO> getMenus(List<ResourceInfo> resourceInfos) {
        List<MenuDTO> menuDTOList = new ArrayList<>();
        //获取一级菜单
        List<ResourceInfo> firstLevelResources = resourceInfos.stream()
                .filter(resourceInfo -> ResourceTypeEnum.MENU.getCode().equals(resourceInfo.getResourceType())).collect(Collectors.toList());
        resourceInfos.removeAll(firstLevelResources);
        for (ResourceInfo firstResource : firstLevelResources) {
            Long pid = firstResource.getId();
            MenuDTO menuDTO = new MenuDTO();
            BeanUtils.copyProperties(firstResource, menuDTO);
            List<ResourceInfo> subResources = resourceInfos.stream()
                    .filter(resourceInfo -> pid.equals(resourceInfo.getPid())).collect(Collectors.toList());
            boolean permission = getSubMenus(menuDTO.getSubMenuDTOList(), subResources, resourceInfos);
            menuDTO.setPermission(permission ? permission : Objects.nonNull(firstResource.getResourceId()));
            menuDTOList.add(menuDTO);
        }
        return menuDTOList;
    }

    private boolean getSubMenus(List<MenuDTO> subMenuList, List<ResourceInfo> resources, List<ResourceInfo> allresources) {
        final AtomicBoolean permission = new AtomicBoolean(false);
        for (ResourceInfo resourceInfo : resources) {
            MenuDTO menuDTO = new MenuDTO();
            BeanUtils.copyProperties(resourceInfo, menuDTO);
            Long id = menuDTO.getId();
            menuDTO.setPermission(Objects.nonNull(resourceInfo.getResourceId()));
            List<ResourceInfo> subResources = allresources.stream()
                    .filter(r -> id.equals(r.getPid())).collect(Collectors.toList());
            subMenuList.add(menuDTO);
            if (!CollectionUtils.isEmpty(subResources)) {
                boolean subPermission = getSubMenus(menuDTO.getSubMenuDTOList(), subResources, allresources);
                if (!permission.get()) {
                    permission.set(subPermission);
                }
                menuDTO.setPermission(subPermission);
            } else {
                if (!permission.get()) {
                    permission.set(menuDTO.getPermission());
                }
            }
        }
        return permission.get();
    }


    @Override
    public List<ResourceInfo> listOperResources() {
        return resourceInfoRepository.listOperResources();
    }
}
