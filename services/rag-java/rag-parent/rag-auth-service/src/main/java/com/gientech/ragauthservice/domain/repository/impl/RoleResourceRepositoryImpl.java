package com.gientech.ragauthservice.domain.repository.impl;

import cn.hutool.core.bean.BeanUtil;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.gientech.ragauthservice.domain.entity.RoleResource;
import com.gientech.ragauthservice.domain.mapper.RoleResourceMapper;
import com.gientech.ragauthservice.domain.model.RoleResourceDO;
import com.gientech.ragauthservice.domain.repository.RoleResourceRepository;
import com.gientech.ragcommon.auth.enums.IsDtlEnums;
import com.gientech.ragcommon.auth.enums.StatusEnums;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import org.apache.commons.compress.utils.Lists;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;
import org.springframework.util.CollectionUtils;

import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Objects;

@Repository
public class RoleResourceRepositoryImpl implements RoleResourceRepository {

    @Autowired
    private RoleResourceMapper roleResourceMapper;

    @Override
    public Boolean addRoleResource(Long roleId, List<Long> resourceIds) {
        if (Objects.isNull(roleId) || CollectionUtils.isEmpty(resourceIds)) {
            return false;
        }
        User user = UserContext.getUser();
        String userName = user.getUserName();
        Date now = new Date();
        List<RoleResourceDO> roleResourceDOS = new ArrayList<>(resourceIds.size());
        resourceIds.forEach(resourceId -> {
            RoleResourceDO roleResourceDO = new RoleResourceDO();
            roleResourceDO.setIsDtl(IsDtlEnums.NO.getCode());
            roleResourceDO.setCreateBy(userName);
            roleResourceDO.setUpdateBy(userName);
            roleResourceDO.setGmtCreate(now);
            roleResourceDO.setGmtModified(now);
            roleResourceDO.setRoleId(roleId);
            roleResourceDO.setResourceId(resourceId);
            roleResourceDO.setStatus(StatusEnums.ENABLED.getCode());
            roleResourceDOS.add(roleResourceDO);
        });
        roleResourceMapper.saveBatch(roleResourceDOS);
        return true;
    }

    @Override
    public Boolean delRoleResource(Long roleId, List<Long> delResourceIds) {
        if (Objects.isNull(roleId) || CollectionUtils.isEmpty(delResourceIds)) {
            return false;
        }
        QueryWrapper<RoleResourceDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("role_id", roleId)
                .in("resource_id", delResourceIds);
        RoleResourceDO resourceDO = new RoleResourceDO();
        resourceDO.setIsDtl(IsDtlEnums.YES.getCode());
        return roleResourceMapper.update(resourceDO, queryWrapper) > 0;
    }

    @Override
    public List<RoleResource> listByRoleId(Long roleId) {
        QueryWrapper<RoleResourceDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("role_id", roleId);
        queryWrapper.eq("status", StatusEnums.ENABLED.getCode());
        queryWrapper.eq("is_dtl", IsDtlEnums.NO.getCode());
        List<RoleResourceDO> roleResourceDOS = roleResourceMapper.selectList(queryWrapper);
        return CollectionUtils.isEmpty(roleResourceDOS) ? Lists.newArrayList() : BeanUtil.copyToList(roleResourceDOS, RoleResource.class);
    }
}
