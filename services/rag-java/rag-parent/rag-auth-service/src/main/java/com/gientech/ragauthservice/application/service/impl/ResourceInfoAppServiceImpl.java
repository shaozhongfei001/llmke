package com.gientech.ragauthservice.application.service.impl;

import cn.hutool.core.bean.BeanUtil;
import com.alibaba.fastjson2.JSON;
import com.gientech.ragauthservice.application.service.ResourceInfoAppService;
import com.gientech.ragauthservice.domain.entity.ResourceInfo;
import com.gientech.ragauthservice.domain.entity.UserRole;
import com.gientech.ragauthservice.domain.service.ResourceInfoDomainService;
import com.gientech.ragauthservice.domain.service.UserRoleDomainService;
import com.gientech.ragauthservice.interfaces.dto.ResourceInfoDTO;
import com.gientech.ragcommon.auth.dto.MenuDTO;
import com.gientech.ragcommon.auth.request.AddResourceReq;
import com.gientech.ragcommon.auth.request.UpdateResourceReq;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.gientech.start.redisson.utils.RedissonUtils;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Objects;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.stream.Collectors;

import static com.gientech.ragcommon.infrastructure.emuns.RedisKeyEnums.AUTH_USER_MENU;

@Service
public class ResourceInfoAppServiceImpl implements ResourceInfoAppService {

    @Autowired
    private ResourceInfoDomainService resourceInfoDomainService;

    @Autowired
    private RedissonUtils redissonUtils;

    @Autowired
    private UserRoleDomainService userRoleDomainService;

    @Override
    public Boolean addResource(AddResourceReq addResourceReq) {
        Long pid = addResourceReq.getPid();
        String url = addResourceReq.getUrl();
        ResourceInfo resourceInfo = resourceInfoDomainService.queryByPidAndUrl(pid, url);
        if (!Objects.isNull(resourceInfo)) {
            throw new ApplicationException(ErrCodeEnum.RESOURCE_URL_REPEAT);
        }
        return resourceInfoDomainService.addResource(BeanUtil.copyProperties(addResourceReq, ResourceInfo.class));
    }

    @Override
    public Boolean deleteResource(Long resourceId) {
        return resourceInfoDomainService.deleteResource(resourceId);
    }

    @Override
    public Boolean updateResource(UpdateResourceReq updateResourceReq) {
        Long pid = updateResourceReq.getPid();
        String url = updateResourceReq.getUrl();
        ResourceInfo resourceInfo = resourceInfoDomainService.queryByPidAndUrl(pid, url);
        if (!Objects.isNull(resourceInfo)) {
            throw new ApplicationException(ErrCodeEnum.RESOURCE_URL_REPEAT);
        }
        return resourceInfoDomainService.updateResource(BeanUtil.copyProperties(updateResourceReq, ResourceInfo.class));
    }

    @Override
    public List<MenuDTO> getMenusByRole(Long roleId) {
        List<ResourceInfo> resourceInfoList = resourceInfoDomainService.queryVisibleByRoleIds(Arrays.asList(roleId));
        if (CollectionUtils.isEmpty(resourceInfoList)) {
            return null;
        }
        return getMenus(resourceInfoList);
    }

    @Override
    public List<MenuDTO> getMenusByUser() {
        User user = UserContext.getUser();
        String userName = user.getUserName();
        //从缓存中获取
        String menusStr = redissonUtils.get(AUTH_USER_MENU + userName);
        return StringUtils.isNotBlank(menusStr) ? JSON.parseArray(menusStr, MenuDTO.class) : List.of();
//        if (StringUtils.isNotBlank(menusStr)) {
//            return JSON.parseArray(menusStr, MenuDTO.class);
//        }
//        throw new ApplicationException(ErrCodeEnum.LOGIN_EXPIRE);
    }

    @Override
    public List<MenuDTO> getAllMenus() {
        List<ResourceInfo> resourceInfoList = resourceInfoDomainService.queryVisibleByRoleIds(Arrays.asList(-1l));
        if (CollectionUtils.isEmpty(resourceInfoList)) {
            return null;
        }
        return getMenus(resourceInfoList);
    }

    @Override
    public List<MenuDTO> getMenus() {
        User user = UserContext.getUser();
        String userId = user.getUserId();
        List<UserRole> userRoles = userRoleDomainService.queryByUserId(Long.parseLong(userId));
        List<ResourceInfo> resourceInfoList = resourceInfoDomainService.queryVisibleByRoleIds(userRoles.stream().map(UserRole::getRoleId).collect(Collectors.toList()));
        if (CollectionUtils.isEmpty(resourceInfoList)) {
            return null;
        }
        return getMenus(resourceInfoList);
    }

    private List<MenuDTO> getMenus(List<ResourceInfo> resourceInfos) {
        List<MenuDTO> menuDTOList = new ArrayList<>();
        //获取一级菜单
        List<ResourceInfo> firstLevelResources = resourceInfos.stream()
                .filter(resourceInfo -> Objects.isNull(resourceInfo.getPid())).collect(Collectors.toList());
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
                getSubMenus(menuDTO.getSubMenuDTOList(), subResources, allresources);
            }
        }
        return permission.get();
    }

    @Override
    public List<MenuDTO> listOperResources() {
        List<ResourceInfo> resourceInfos = resourceInfoDomainService.listOperResources();
        return getMenus(resourceInfos);
    }
}
