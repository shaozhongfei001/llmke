package com.gientech.ragauthservice.domain.service.impl;


import cn.hutool.core.bean.BeanUtil;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragauthservice.domain.entity.DepartmentInfo;
import com.gientech.ragauthservice.domain.entity.UserGroup;
import com.gientech.ragauthservice.domain.entity.UserInfo;
import com.gientech.ragauthservice.domain.model.UserInfoDO;
import com.gientech.ragauthservice.domain.repository.UserGroupRepository;
import com.gientech.ragauthservice.domain.service.UserGroupDomainService;
import com.google.common.collect.Maps;
import org.apache.commons.compress.utils.Lists;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;

import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;

/**
 * <p>
 * 机构-用户关联表 服务实现类
 * </p>
 *
 * @author wudf
 * @since 2024-07-23
 */
@Service
public class UserGroupDomainServiceImpl implements UserGroupDomainService {

    @Autowired
    private UserGroupRepository userGroupRepository;

    @Override
    public List<UserGroup> findByGroupId(Long groupId) {
        if (Objects.isNull(groupId))
            return Lists.newArrayList();
        return userGroupRepository.findByGroupId(groupId);
    }

    @Override
    public void addUsers(Long groupId, List<Long> addUserIds) {
        userGroupRepository.saveUsers(groupId, addUserIds);
    }

    @Override
    public void delUsers(Long groupId, List<Long> delUserIds) {
        userGroupRepository.delUser(groupId, delUserIds);
    }

    @Override
    public Page<UserGroup> groupUserList(Long groupId, Long pageNo, Long pageSize) {
        return userGroupRepository.groupUserList(groupId, pageNo, pageSize);
    }

    @Override
    public Page<UserInfo> flatUserList(Long groupId, Long pageNo, Long pageSize) {
        Page<UserInfoDO> userInfoDOPage = userGroupRepository.flatUserList(groupId, pageNo, pageSize);
        Page<UserInfo> userInfoPage = new Page<>();
        BeanUtil.copyProperties(userInfoDOPage,userInfoPage);
        List<UserInfo> userInfos = BeanUtil.copyToList(userInfoPage.getRecords(), UserInfo.class);
        userInfoPage.setRecords(userInfos);
        return userInfoPage;
    }

    @Override
    public Long userCount(Long groupId) {
        if (Objects.isNull(groupId))
            return 0L;
        return userGroupRepository.userCount(groupId);
    }

    @Override
    public Map<Long, UserGroup> findByIds(List<Long> groupIds) {
        if (CollectionUtils.isEmpty(groupIds))
            return Maps.newHashMap();
        return userGroupRepository.findByGroupIds(groupIds);
    }


    @Override
    public List<Long> listGroupIdsByUserId(Long userId) {
        if (Objects.isNull(userId))
            return Lists.newArrayList();
        return userGroupRepository.listGroupIdsByUserId(userId);
    }

    @Override
    public List<UserInfo> getUserListByGroupList(List<Long> groupIds) {
        if (CollectionUtils.isEmpty(groupIds)) {
            return Lists.newArrayList();
        }
        return userGroupRepository.getUserListByGroupList(groupIds);
    }

    @Override
    public List<DepartmentInfo> getDepartmentListByGroupId(Long groupId) {
        return userGroupRepository.getDeptListByGroupId(groupId);
    }

    @Override
    public void addDepartments(Long groupId, List<Long> addDeptIds) {
        userGroupRepository.saveDepartments(groupId, addDeptIds);
    }

    @Override
    public void delDepartments(Long groupId, List<Long> delDeptIds) {
        userGroupRepository.delDepartments(groupId, delDeptIds);
    }

    @Override
    public List<Long> listGroupIdsByDeptId(Long deptId) {
        if (Objects.isNull(deptId))
            return Lists.newArrayList();
        return userGroupRepository.listGroupIdsByDeptId(deptId);
    }

    @Override
    public Long groupUserCount(Long groupId) {
        return Optional.ofNullable(groupId)
                .map(userGroupRepository::groupUserCount)
                .orElse(0L);
    }
}
