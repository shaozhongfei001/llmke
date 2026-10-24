package com.gientech.ragauthservice.domain.repository.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.collection.CollUtil;
import com.baomidou.mybatisplus.core.conditions.Wrapper;
import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragauthservice.domain.entity.DepartmentInfo;
import com.gientech.ragauthservice.domain.entity.UserGroup;
import com.gientech.ragauthservice.domain.entity.UserInfo;
import com.gientech.ragauthservice.domain.mapper.UserGroupMapper;
import com.gientech.ragauthservice.domain.model.UserGroupDO;
import com.gientech.ragauthservice.domain.model.UserInfoDO;
import com.gientech.ragauthservice.domain.repository.UserGroupRepository;
import com.gientech.ragcommon.auth.enums.DeptIsDelEnums;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import org.apache.commons.compress.utils.Lists;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Repository;
import org.springframework.util.CollectionUtils;

import java.util.*;

/**
 * <p>
 * 机构-用户关联表 服务类
 * </p>
 *
 * @author wudf
 * @since 2024-07-23
 */
@Repository
public class UserGroupRepositoryImpl implements UserGroupRepository {

    @Autowired
    private UserGroupMapper userGroupMapper;

    @Override
    public List<UserGroup> findByGroupId(Long groupId) {
        QueryWrapper<UserGroupDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("group_id", groupId).eq("is_del", DeptIsDelEnums.NO.getCode());
        List<UserGroupDO> authDataUserGroupDOS = userGroupMapper.selectList(queryWrapper);
        return CollectionUtils.isEmpty(authDataUserGroupDOS) ? Lists.newArrayList() : BeanUtil.copyToList(authDataUserGroupDOS, UserGroup.class);
    }

    @Override
    public void delUser(Long groupId, List<Long> delUserIds) {
        if (Objects.isNull(groupId) || CollectionUtils.isEmpty(delUserIds))
            return;
        QueryWrapper<UserGroupDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("group_id", groupId);
        queryWrapper.in("user_id", delUserIds);

        UserGroupDO userGroupDO = new UserGroupDO();
        userGroupDO.setIsDel(DeptIsDelEnums.YES.getCode());
        userGroupMapper.update(userGroupDO,queryWrapper);
    }

    @Override
    public void saveUsers(Long groupId, List<Long> addUserIds) {
        if (Objects.isNull(groupId) || CollectionUtils.isEmpty(addUserIds))
            return;
        User user = UserContext.getUser();
        String userName = user.getUserName();
        Date date = new Date();
        List<UserGroup> authDataUserGroups = new ArrayList<>();
        addUserIds.forEach(userId -> {
            UserGroup authDataUserGroup = new UserGroup();
            authDataUserGroup.setGroupId(groupId);
            authDataUserGroup.setUserId(userId);
            authDataUserGroup.setCreateBy(userName);
            authDataUserGroup.setUpdateBy(userName);
            authDataUserGroup.setGmtCreate(date);
            authDataUserGroup.setGmtModified(date);
            authDataUserGroups.add(authDataUserGroup);
        });
        userGroupMapper.saveBatch(BeanUtil.copyToList(authDataUserGroups, UserGroupDO.class));
    }

    @Override
    public Page<UserGroup> groupUserList(Long groupId, Long pageNo, Long pageSize) {
        QueryWrapper<UserGroupDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("group_id", groupId)
                .eq("is_del",DeptIsDelEnums.NO.getCode());
        Page<UserGroupDO> page = new Page<>(pageNo, pageSize);
        Page<UserGroupDO> authDataGroupDOPage = userGroupMapper.selectPage(page, queryWrapper);
        Page<UserGroup> pageResult = new Page<>();
        BeanUtil.copyProperties(authDataGroupDOPage, pageResult);
        pageResult.setRecords(BeanUtil.copyToList(authDataGroupDOPage.getRecords(), UserGroup.class));
        return pageResult;
    }

    @Override
    public Long userCount(Long groupId) {
        QueryWrapper<UserGroupDO> queryWrapper = new QueryWrapper<>();
        queryWrapper.eq("group_id", groupId)
                .eq("is_del",DeptIsDelEnums.NO.getCode());
        return userGroupMapper.selectCount(queryWrapper);
    }

    @Override
    public Map<Long, UserGroup> findByGroupIds(List<Long> groupIds) {
        return userGroupMapper.findByGroupIds(groupIds);
    }

    @Override
    public List<Long> listGroupIdsByUserId(Long userId) {
        LambdaQueryWrapper<UserGroupDO> wrapper = Wrappers.lambdaQuery(UserGroupDO.class)
                .select(UserGroupDO::getGroupId)
                .eq(UserGroupDO::getUserId, userId)
                .eq(UserGroupDO::getIsDel, DeptIsDelEnums.NO.getCode());
        List<UserGroupDO> userGroupDOS = userGroupMapper.selectList(wrapper);
        return CollUtil.isEmpty(userGroupDOS) ? Lists.newArrayList() : userGroupDOS.stream().map(UserGroupDO::getGroupId).toList();
    }

    @Override
    public List<UserInfo> getUserListByGroupList(List<Long> groupIds) {
        if (CollectionUtils.isEmpty(groupIds)) {
            return Lists.newArrayList();
        }
        return userGroupMapper.getUserListByGroupList(groupIds);
    }

    @Override
    public List<DepartmentInfo> getDeptListByGroupId(Long groupId) {
        return userGroupMapper.getDeptListByGroupId(groupId);
    }

    @Override
    public Page<UserInfoDO> flatUserList(Long groupId, Long pageNo, Long pageSize) {
        Page<UserInfoDO> page = new Page<>(pageNo, pageSize);
        return userGroupMapper.flatUserList(groupId, page);
    }
    @Override
    public void saveDepartments(Long groupId, List<Long> addDeptIds) {
        if (Objects.isNull(groupId) || CollectionUtils.isEmpty(addDeptIds))
            return;

        List<UserGroupDO> userGroupDOList = addDeptIds.stream()
                .map(deptId -> UserGroupDO.builder()
                        .groupId(groupId)
                        .deptId(deptId)
                        .createBy(UserContext.getUser().getUserName())
                        .updateBy(UserContext.getUser().getUserName())
                        .gmtCreate(new Date())
                        .gmtModified(new Date())
                        .build())
                .toList();

        userGroupMapper.saveBatch(userGroupDOList);
    }

    @Override
    public void delDepartments(Long groupId, List<Long> delDeptIds) {
        if (Objects.isNull(groupId) || CollectionUtils.isEmpty(delDeptIds))
            return;
        LambdaQueryWrapper<UserGroupDO> queryWrapper = Wrappers.lambdaQuery(UserGroupDO.class)
                .eq(UserGroupDO::getGroupId, groupId)
                .in(UserGroupDO::getDeptId, delDeptIds);

        UserGroupDO userGroupDO = new UserGroupDO();
        userGroupDO.setIsDel(DeptIsDelEnums.YES.getCode());
        userGroupMapper.update(userGroupDO,queryWrapper);
    }

    @Override
    public List<Long> listGroupIdsByDeptId(Long deptId) {
        LambdaQueryWrapper<UserGroupDO> wrapper = Wrappers.lambdaQuery(UserGroupDO.class)
                .select(UserGroupDO::getGroupId)
                .eq(UserGroupDO::getIsDel,DeptIsDelEnums.NO.getCode())
                .eq(UserGroupDO::getDeptId, deptId);
        List<UserGroupDO> userGroupDOS = userGroupMapper.selectList(wrapper);
        return CollUtil.isEmpty(userGroupDOS) ? Lists.newArrayList() : userGroupDOS.stream().map(UserGroupDO::getGroupId).toList();
    }

    @Override
    public Long groupUserCount(Long groupId) {
        Wrapper<UserGroupDO> queryWrapper = Wrappers.lambdaQuery(UserGroupDO.class)
                .eq(UserGroupDO::getGroupId, groupId)
                .eq(UserGroupDO::getIsDel,DeptIsDelEnums.NO.getCode())
                .isNotNull(UserGroupDO::getUserId);

        return userGroupMapper.selectCount(queryWrapper);
    }

}
