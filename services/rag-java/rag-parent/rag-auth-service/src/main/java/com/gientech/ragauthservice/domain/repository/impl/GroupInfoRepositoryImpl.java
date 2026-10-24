package com.gientech.ragauthservice.domain.repository.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.collection.CollUtil;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragauthservice.domain.entity.GroupInfo;
import com.gientech.ragauthservice.domain.mapper.GroupInfoMapper;
import com.gientech.ragauthservice.domain.model.GroupInfoDO;
import com.gientech.ragauthservice.domain.repository.GroupInfoRepository;
import com.gientech.ragcommon.auth.enums.GroupIsDelEnums;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import com.google.common.collect.Lists;
import org.apache.commons.lang3.StringUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;
import org.springframework.util.CollectionUtils;

import java.util.*;

/**
 * <p>
 * 机构组 服务类
 * </p>
 *
 * @author wudf
 * @since 2024-07-23
 */
@Repository
public class GroupInfoRepositoryImpl implements GroupInfoRepository {

    @Autowired
    private GroupInfoMapper groupMapper;

    @Override
    public GroupInfo findByName(String name) {
        QueryWrapper<GroupInfoDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("name", name)
                .eq("is_del", GroupIsDelEnums.NO.getCode()).
                last("limit 1");
        GroupInfoDO authDataGroupDO = groupMapper.selectOne(queryWrapper);
        return Objects.isNull(authDataGroupDO) ? null : BeanUtil.copyProperties(authDataGroupDO, GroupInfo.class);
    }

    @Override
    public Boolean addGroup(GroupInfo authDataGroup) {
        User user = UserContext.getUser();
        String userName = user.getUserName();

        authDataGroup.setCreateBy(userName);
        authDataGroup.setUpdateBy(userName);
        authDataGroup.setGmtCreate(new Date());
        authDataGroup.setGmtModified(authDataGroup.getGmtCreate());

        return groupMapper.insert(BeanUtil.copyProperties(authDataGroup, GroupInfoDO.class)) > 0;
    }

    @Override
    public Boolean updateGroup(GroupInfo authDataGroup) {
        User user = UserContext.getUser();
        String userName = user.getUserName();
        GroupInfoDO authDataGroupDO = BeanUtil.copyProperties(authDataGroup, GroupInfoDO.class);
        authDataGroupDO.setUpdateBy(userName);
        authDataGroupDO.setGmtModified(new Date());
        return groupMapper.updateById(authDataGroupDO) > 0;
    }

    @Override
    public GroupInfo findById(Long id) {
        if (Objects.isNull(id))
            return null;
        QueryWrapper<GroupInfoDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("is_del",GroupIsDelEnums.NO.getCode())
                .eq("id",id)
                .last("lmit 1");

        GroupInfoDO authDataGroupDO = groupMapper.selectOne(queryWrapper);
        return Objects.isNull(authDataGroupDO) ? null : BeanUtil.copyProperties(authDataGroupDO, GroupInfo.class);
    }

    @Override
    public Boolean deleteGroup(Long id) {
        if (Objects.isNull(id))
            return false;
        GroupInfoDO groupInfoDO = new GroupInfoDO();
        groupInfoDO.setId(id);
        groupInfoDO.setIsDel(GroupIsDelEnums.YES.getCode());
        return groupMapper.updateById(groupInfoDO) > 0;
    }

    @Override
    public Page<GroupInfo> list(String name, Long pageNo, Long pageSize) {
        QueryWrapper<GroupInfoDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("is_del",GroupIsDelEnums.NO.getCode());
        if (StringUtils.isNotBlank(name))
            queryWrapper.like("name", name);
        Page<GroupInfoDO> page = new Page<>(pageNo, pageSize);
        Page<GroupInfoDO> authDataGroupDOPage = groupMapper.selectPage(page, queryWrapper);
        Page<GroupInfo> pageResult = new Page<>();
        BeanUtil.copyProperties(authDataGroupDOPage, pageResult);
        pageResult.setRecords(CollUtil.isEmpty(authDataGroupDOPage.getRecords()) ? Lists.newArrayList() : BeanUtil.copyToList(authDataGroupDOPage.getRecords(), GroupInfo.class));
        return pageResult;
    }

    @Override
    public Map<Long, GroupInfo> findByIds(List<Long> groupIds) {
        Map<Long,GroupInfo> resutMap = new HashMap<>();
        if (CollectionUtils.isEmpty(groupIds))
            return resutMap;
        Map<Long,GroupInfoDO> groupInfoDOMap = groupMapper.findByIds(groupIds);
        if(CollectionUtils.isEmpty(groupInfoDOMap)){
            return resutMap;
        }
        groupInfoDOMap.forEach((id,groupInfoDO)->{
            resutMap.put(id,BeanUtil.copyProperties(groupInfoDO,GroupInfo.class));
        });
        return resutMap;
    }
}
