package com.gientech.ragauthservice.domain.repository.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.collection.CollUtil;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.gientech.ragauthservice.domain.entity.GroupPrivilege;
import com.gientech.ragauthservice.domain.mapper.GroupPrivilegeMapper;
import com.gientech.ragauthservice.domain.model.GroupPrivilegeDO;
import com.gientech.ragauthservice.domain.repository.GroupPrivilegeRepository;
import com.gientech.ragauthservice.infrastructure.convertor.GroupPrivilegeConvertor;
import com.gientech.ragcommon.auth.enums.GroupPrivilegeIsDelEnums;
import com.gientech.ragcommon.auth.request.GroupPrivilegeReq;
import com.gientech.ragcommon.auth.request.UpdateGroupPermissionReq;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import org.apache.commons.compress.utils.Lists;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;
import org.springframework.util.CollectionUtils;

import java.util.Date;
import java.util.List;
import java.util.Objects;

@Repository
public class GroupPrivilegeRepositoryImpl implements GroupPrivilegeRepository {

    @Autowired
    private GroupPrivilegeMapper groupPrivilegeMapper;

    @Override
    public void delete(Integer bizType, Long targetId, List<Long> groupIds) {
        if (Objects.isNull(bizType) || Objects.isNull(targetId) || CollectionUtils.isEmpty(groupIds))
            return;
        QueryWrapper<GroupPrivilegeDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("biz_type", bizType)
                .eq("target_id", targetId)
                .in("group_id", groupIds);
        GroupPrivilegeDO groupPrivilegeDO = new GroupPrivilegeDO();
        groupPrivilegeDO.setIsDel(GroupPrivilegeIsDelEnums.YES.getCode());
        groupPrivilegeMapper.update(groupPrivilegeDO,queryWrapper);
    }

    @Override
    public void addBatch(GroupPrivilegeReq groupPrivilegeReq) {

        List<Long> groupIds = groupPrivilegeReq.getGroupIds();
        Long targetId = groupPrivilegeReq.getTargetId();
        Integer bizType = groupPrivilegeReq.getBizType();
        Integer permission = groupPrivilegeReq.getPermission();

        User user = UserContext.getUser();
        String userName = user.getUserName();
        Date date = new Date();

        List<GroupPrivilegeDO> groupPrivilegeDOS = Lists.newArrayList();
        groupIds.forEach(groupId -> {
            GroupPrivilegeDO groupPrivilege = new GroupPrivilegeDO();
            groupPrivilege.setGroupId(groupId);
            groupPrivilege.setBizType(bizType);
            groupPrivilege.setTargetId(targetId);
            groupPrivilege.setPermission(permission);
            groupPrivilege.setUpdateBy(userName);
            groupPrivilege.setCreateBy(userName);
            groupPrivilege.setGmtModified(date);
            groupPrivilege.setGmtCreate(date);
            groupPrivilegeDOS.add(groupPrivilege);
        });
        groupPrivilegeMapper.saveBatch(groupPrivilegeDOS);
    }

    @Override
    public int updatePermissionBatch(List<Long> ids, Integer permission, Long elementId) {
        if (CollUtil.isEmpty(ids)) {
            return 0;
        }
        return groupPrivilegeMapper.updatePermissionBatch(ids, permission, elementId);
    }

    @Override
    public void addBatchWithList(List<GroupPrivilege> groupPrivileges) {
        groupPrivilegeMapper.saveBatch(GroupPrivilegeConvertor.INSTANCE.groupPrivileges2DOS(groupPrivileges));
    }

    @Override
    public Boolean deleteById(Long id) {
        if (Objects.isNull(id))
            return false;
        GroupPrivilegeDO groupPrivilegeDO = new GroupPrivilegeDO();
        groupPrivilegeDO.setId(id);
        groupPrivilegeDO.setIsDel(GroupPrivilegeIsDelEnums.YES.getCode());
        return groupPrivilegeMapper.updateById(groupPrivilegeDO) > 0;
    }

    @Override
    public GroupPrivilege findbyCondtion(UpdateGroupPermissionReq groupPermissionReq) {
        Long groupId = groupPermissionReq.getGroupId();
        Integer bizType = groupPermissionReq.getBizType();
        Long targetId = groupPermissionReq.getTargetId();
        QueryWrapper<GroupPrivilegeDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("biz_type", bizType)
                .eq("target_id", targetId)
                .eq("group_id", groupId)
                .eq("is_del", GroupPrivilegeIsDelEnums.NO.getCode())
                .last("limit 1");
        GroupPrivilegeDO groupPrivilegeDO = groupPrivilegeMapper.selectOne(queryWrapper);
        return Objects.isNull(groupPrivilegeDO) ? null : BeanUtil.copyProperties(groupPrivilegeDO, GroupPrivilege.class);
    }

    @Override
    public Boolean updateById(GroupPrivilege groupPrivilege) {
        groupPrivilege.setGmtModified(new Date());
        groupPrivilege.setUpdateBy(UserContext.getUser().getUserName());
        return groupPrivilegeMapper.updateById(BeanUtil.copyProperties(groupPrivilege, GroupPrivilegeDO.class)) > 0;
    }

    @Override
    public List<GroupPrivilege> findbyTypeAndId(Integer bizType, Long targetId) {
        if (Objects.isNull(bizType) || Objects.isNull(targetId))
            return null;
        QueryWrapper<GroupPrivilegeDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("biz_type", bizType)
                .eq("is_del", GroupPrivilegeIsDelEnums.NO.getCode())
                .eq("target_id", targetId);
        List<GroupPrivilegeDO> groupPrivilegeList = groupPrivilegeMapper.selectList(queryWrapper);
        return CollectionUtils.isEmpty(groupPrivilegeList) ? Lists.newArrayList() : BeanUtil.copyToList(groupPrivilegeList, GroupPrivilege.class);
    }


    @Override
    public List<GroupPrivilege> findByTypeAndGroupIds(Integer bizType, List<Long> groupIdList, List<Long> targetIds) {
        if (Objects.isNull(bizType) || CollUtil.isEmpty(groupIdList))
            return Lists.newArrayList();

        LambdaQueryWrapper<GroupPrivilegeDO> wrapper = Wrappers.lambdaQuery(GroupPrivilegeDO.class)
                .eq(GroupPrivilegeDO::getBizType, bizType)
                .eq(GroupPrivilegeDO::getIsDel, GroupPrivilegeIsDelEnums.NO.getCode())
                .in(!CollectionUtils.isEmpty(targetIds), GroupPrivilegeDO::getTargetId, targetIds)
                .in(GroupPrivilegeDO::getGroupId, groupIdList);
        List<GroupPrivilegeDO> groupPrivilegeDOS = groupPrivilegeMapper.selectList(wrapper);
        return CollUtil.isEmpty(groupPrivilegeDOS) ? Lists.newArrayList() : BeanUtil.copyToList(groupPrivilegeDOS, GroupPrivilege.class);
    }

    @Override
    public List<GroupPrivilege> list(GroupPrivilege groupPrivilege) {
        LambdaQueryWrapper<GroupPrivilegeDO> wrapper = Wrappers.lambdaQuery(GroupPrivilegeDO.class)
                .eq(GroupPrivilegeDO::getBizType, groupPrivilege.getBizType())
                .eq(GroupPrivilegeDO::getTargetId, groupPrivilege.getTargetId())
                .eq(GroupPrivilegeDO::getGroupId, groupPrivilege.getGroupId())
                .eq(GroupPrivilegeDO::getIsDel, GroupPrivilegeIsDelEnums.NO.getCode())
                .eq(GroupPrivilegeDO::getPermission, groupPrivilege.getPermission());
        List<GroupPrivilegeDO> groupPrivilegeDOS = groupPrivilegeMapper.selectList(wrapper);
        return CollUtil.isEmpty(groupPrivilegeDOS) ? Lists.newArrayList() : BeanUtil.copyToList(groupPrivilegeDOS, GroupPrivilege.class);
    }
}
