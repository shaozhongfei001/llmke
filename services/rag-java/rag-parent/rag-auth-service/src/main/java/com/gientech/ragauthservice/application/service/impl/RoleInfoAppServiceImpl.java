package com.gientech.ragauthservice.application.service.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.collection.CollUtil;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragauthservice.application.service.RoleInfoAppService;
import com.gientech.ragauthservice.domain.entity.ResourceInfo;
import com.gientech.ragauthservice.domain.entity.RoleInfo;
import com.gientech.ragauthservice.domain.entity.UserRole;
import com.gientech.ragauthservice.domain.service.ResourceInfoDomainService;
import com.gientech.ragauthservice.domain.service.RoleInfoDomainService;
import com.gientech.ragauthservice.domain.service.RoleResourceDomainService;
import com.gientech.ragauthservice.domain.service.UserRoleDomainService;
import com.gientech.ragauthservice.infrastructure.AuthProperties;
import com.gientech.ragcommon.auth.dto.RoleInfoDTO;
import com.gientech.ragcommon.auth.enums.RoleTypeEnums;
import com.gientech.ragcommon.auth.request.SearchRoleListReq;
import com.gientech.ragcommon.auth.request.AddRoleReq;
import com.gientech.ragcommon.auth.request.UpdateRoleReq;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.CollectionUtils;

import java.util.*;
import java.util.stream.Collectors;

@Service
public class RoleInfoAppServiceImpl implements RoleInfoAppService {

    @Autowired
    private RoleInfoDomainService roleInfoDomainService;

    @Autowired
    private ResourceInfoDomainService resourceInfoDomainService;

    @Autowired
    private RoleResourceDomainService roleResourceDomainService;

    @Autowired
    private UserRoleDomainService userRoleDomainService;

    @Autowired
    private AuthProperties authProperties;

    @Override
    public Boolean addRole(AddRoleReq addRoleReq) {
        RoleInfo roleInfo = roleInfoDomainService.queryByName(addRoleReq.getName());
        if (!Objects.isNull(roleInfo)) {
            throw new ApplicationException(ErrCodeEnum.ROLE_NAME_REPEAT);
        }
        roleInfo = BeanUtil.copyProperties(addRoleReq, RoleInfo.class);
        roleInfoDomainService.addRole(roleInfo);
        roleResourceDomainService.addRoleResource(roleInfo.getId(),addRoleReq.getResourceIds());
        return true;
    }

    @Transactional
    @Override
    public Boolean updateRole(UpdateRoleReq updateRoleReq) {
        Long roleId = updateRoleReq.getId();
        String name = updateRoleReq.getName();
        if(isAdmin(roleId))
            throw new ApplicationException(ErrCodeEnum.ROLE_ADMIN_NO_UPDATE);
        RoleInfo roleInfo = roleInfoDomainService.queryById(roleId,name);
        if(Objects.isNull(roleInfo)){
            RoleInfo roleByName = roleInfoDomainService.queryByName(name);
            if (!Objects.isNull(roleByName)) {
                throw new ApplicationException(ErrCodeEnum.ROLE_NAME_REPEAT);
            }
        }
        //修改角色
        boolean res = roleInfoDomainService.updateRole(BeanUtil.copyProperties(updateRoleReq, RoleInfo.class));
        if (res) {
            //修改角色对应的资源
            List<ResourceInfo> resourceInfoList = resourceInfoDomainService.queryByRoleIds(Arrays.asList(roleId));
            resourceInfoList = CollectionUtils.isEmpty(resourceInfoList) ? new ArrayList<>() : resourceInfoList;
            List<Long> dbRourceIds = resourceInfoList.stream().map(resourceInfo -> resourceInfo.getId()).collect(Collectors.toList());
            List<Long> resourceIds = updateRoleReq.getResourceIds();
            resourceIds = CollectionUtils.isEmpty(resourceIds) ? new ArrayList<>() : resourceIds;
            List<Long> addResourceIds = (List<Long>) CollUtil.subtract(resourceIds, dbRourceIds);
            List<Long> delResourceIds = (List<Long>) CollUtil.subtract(dbRourceIds, resourceIds);
            roleResourceDomainService.addRoleResource(updateRoleReq.getId(),addResourceIds);
            roleResourceDomainService.delRoleResource(updateRoleReq.getId(),delResourceIds);
        }
        return res;
    }

    private boolean isAdmin(Long roleId) {
        RoleInfo roleInfo = roleInfoDomainService.queryById(roleId);
        if(Objects.nonNull(roleInfo) && roleInfo.getName().equals("管理员"))
            return true;
        return false;
    }

    @Override
    public Boolean deleteRole(Long roleId) {
        List<UserRole> userRoles = userRoleDomainService.queryByRoleId(roleId);
        if(!CollectionUtils.isEmpty(userRoles)){
            throw new ApplicationException(ErrCodeEnum.ROLE_BINDING_USER);
        }
        return roleInfoDomainService.deleteRole(roleId);
    }

    @Override
    public Page<RoleInfoDTO> searchRoleList(SearchRoleListReq searchRoleListReq) {
        String idOrName = searchRoleListReq.getIdOrName();
        Integer status = searchRoleListReq.getStatus();
        Long pageNo = searchRoleListReq.getPageNo();
        Long pageSize = searchRoleListReq.getPageSize();
        Page<RoleInfo> roleInfoPage = roleInfoDomainService.list(idOrName,status,pageNo,pageSize);
        Page<RoleInfoDTO> result = new Page<>();
        BeanUtil.copyProperties(roleInfoPage, result);
        List<RoleInfoDTO> roleInfoDTOS = BeanUtil.copyToList(roleInfoPage.getRecords(), RoleInfoDTO.class);
        roleInfoDTOS.forEach(roleInfo -> {
            if (roleInfo.getId().equals(authProperties.getSuperRoleId()))
                roleInfo.setRoleType(RoleTypeEnums.SUPER_ADMIN.getCode());
            else if (roleInfo.getId().equals(authProperties.getSuperRoleId()))
                roleInfo.setRoleType(RoleTypeEnums.ADMIN.getCode());
        });
        result.setRecords(BeanUtil.copyToList(roleInfoPage.getRecords(), RoleInfoDTO.class));
        return result;
    }

    @Override
    public List<RoleInfoDTO> getByUserId() {
        User user = UserContext.getUser();
        String userId = user.getUserId();
        List<UserRole> userRoles = userRoleDomainService.queryByUserId(Long.parseLong(userId));
        if(CollectionUtils.isEmpty(userRoles)){
            throw new ApplicationException(ErrCodeEnum.NO_ROLE_ERROR);
        }
        List<Long> roleIds = userRoles.stream().map(UserRole::getRoleId).collect(Collectors.toList());
        List<RoleInfo> roleInfos = roleInfoDomainService.queryByIds(roleIds);
        return CollectionUtils.isEmpty(roleInfos) ? null : BeanUtil.copyToList(roleInfos,RoleInfoDTO.class);
    }

    @Override
    public RoleInfoDTO getRoleInfo(Long roleId) {
        RoleInfo roleInfo = roleInfoDomainService.getRoleInfo(roleId);
        return Objects.isNull(roleInfo) ? null : BeanUtil.copyProperties(roleInfo,RoleInfoDTO.class);
    }

    @Override
    public List<RoleInfoDTO> listAll() {
        List<RoleInfo> roleInfos = roleInfoDomainService.listAll();
        return BeanUtil.copyToList(roleInfos,RoleInfoDTO.class);
    }
}
