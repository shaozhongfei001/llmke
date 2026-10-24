package com.gientech.ragauthservice.domain.repository.impl;

import cn.hutool.core.bean.BeanUtil;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.gientech.ragauthservice.domain.entity.ResourceInfo;
import com.gientech.ragauthservice.domain.mapper.ResourceInfoMapper;
import com.gientech.ragauthservice.domain.model.ResourceInfoDO;
import com.gientech.ragauthservice.domain.model.ResourceInfoWithVisibleDO;
import com.gientech.ragauthservice.domain.repository.ResourceInfoRepository;
import com.gientech.ragcommon.auth.enums.ResIsDelEnums;
import com.gientech.ragcommon.auth.enums.ResourceTypeEnum;
import com.gientech.ragcommon.auth.enums.StatusEnums;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import org.apache.commons.collections4.CollectionUtils;
import org.apache.commons.compress.utils.Lists;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;

import java.util.Date;
import java.util.List;
import java.util.Objects;

@Repository
public class ResourceInfoRepositoryImpl implements ResourceInfoRepository {

    @Autowired
    private ResourceInfoMapper resourceInfoMapper;

    @Override
    public List<ResourceInfo> queryByRoleIds(List<Long> roleIds) {
        List<ResourceInfoDO> resourceInfoDOS = resourceInfoMapper.queryByRoleIds(roleIds);
        return CollectionUtils.isEmpty(resourceInfoDOS) ? Lists.newArrayList() : BeanUtil.copyToList(resourceInfoDOS, ResourceInfo.class);
    }

    @Override
    public List<ResourceInfo> queryVisibleByRoleIds(List<Long> roleIds) {
        List<ResourceInfoWithVisibleDO> resourceInfoWithVisibleDOS = resourceInfoMapper.queryVisibleByRoleIds(roleIds);
        return CollectionUtils.isEmpty(resourceInfoWithVisibleDOS) ? null : BeanUtil.copyToList(resourceInfoWithVisibleDOS, ResourceInfo.class);
    }

    @Override
    public ResourceInfo queryByPidAndUrl(Long pid, String url) {
        QueryWrapper<ResourceInfoDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("url", url);
        queryWrapper.eq("is_dtl", ResIsDelEnums.NO.getCode());
        if (!Objects.isNull(pid))
            queryWrapper.eq("pid", pid);
        queryWrapper.last("limit 1");
        ResourceInfoDO resourceInfoDO = resourceInfoMapper.selectOne(queryWrapper);
        return Objects.isNull(resourceInfoDO) ? null : BeanUtil.copyProperties(resourceInfoDO, ResourceInfo.class);
    }

    @Override
    public Boolean save(ResourceInfo resourceInfo) {
        User user = UserContext.getUser();
        String userName = user.getUserName();
        resourceInfo.setCreateBy(userName);
        resourceInfo.setUpdateBy(userName);
        resourceInfo.setGmtCreate(new Date());
        resourceInfo.setGmtModified(resourceInfo.getGmtCreate());
        return resourceInfoMapper.insert(BeanUtil.copyProperties(resourceInfo, ResourceInfoDO.class)) > 0;
    }

    @Override
    public Boolean deleteById(Long resourceId) {
        if (Objects.isNull(resourceId))
            return false;
        ResourceInfoDO resourceInfoDO = new ResourceInfoDO();
        resourceInfoDO.setId(resourceId);
        resourceInfoDO.setIsDtl(ResIsDelEnums.YES.getCode());
        return resourceInfoMapper.updateById(resourceInfoDO) > 0;
    }

    @Override
    public Boolean updateResource(ResourceInfo resourceInfo) {
        User user = UserContext.getUser();
        String userName = user.getUserName();
        resourceInfo.setUpdateBy(userName);
        resourceInfo.setGmtModified(new Date());
        return resourceInfoMapper.updateById(BeanUtil.copyProperties(resourceInfo, ResourceInfoDO.class)) > 0;
    }

    @Override
    public List<ResourceInfo> listOperResources() {
        QueryWrapper<ResourceInfoDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("is_dtl", ResIsDelEnums.NO.getCode());
        queryWrapper.eq("status", StatusEnums.ENABLED.getCode());
        queryWrapper.eq("resource_type", ResourceTypeEnum.OPER.getCode());

        List<ResourceInfoDO> resourceInfoDOS = resourceInfoMapper.selectList(queryWrapper);
        return CollectionUtils.isEmpty(resourceInfoDOS) ? Lists.newArrayList() : BeanUtil.copyToList(resourceInfoDOS, ResourceInfo.class);
    }
}
