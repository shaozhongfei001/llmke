package com.gientech.ragauthservice.application.service.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.collection.CollUtil;
import cn.hutool.core.collection.CollectionUtil;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragauthservice.application.service.DepartmentInfoAppService;
import com.gientech.ragauthservice.application.service.GroupAppService;
import com.gientech.ragauthservice.domain.entity.DepartmentInfo;
import com.gientech.ragauthservice.domain.entity.GroupInfo;
import com.gientech.ragauthservice.domain.entity.UserGroup;
import com.gientech.ragauthservice.domain.entity.UserInfo;
import com.gientech.ragauthservice.domain.service.GroupInfoDomainService;
import com.gientech.ragauthservice.domain.service.UserGroupDomainService;
import com.gientech.ragauthservice.domain.service.UserInfoDomainService;
import com.gientech.ragcommon.auth.dto.FrameElement;
import com.gientech.ragcommon.auth.dto.GroupDTO;
import com.gientech.ragcommon.auth.dto.UserInfoDTO;
import com.gientech.ragcommon.auth.enums.FrameElementTypeEnums;
import com.gientech.ragcommon.auth.request.*;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import org.apache.commons.compress.utils.Lists;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.util.CollectionUtils;

import java.util.List;
import java.util.Objects;
import java.util.Optional;
import java.util.stream.Collectors;

@Service
public class GroupAppServiceImpl implements GroupAppService {

    @Autowired
    private GroupInfoDomainService groupDomainService;

    @Autowired
    private UserGroupDomainService userGroupDomainService;

    @Autowired
    private UserInfoDomainService userInfoDomainService;

    @Autowired
    private DepartmentInfoAppService departmentInfoAppService;

    @Override
    public Boolean addGroup(AddGroupReq addGroupReq) {
        String name = addGroupReq.getName();
        GroupInfo authDataGroup = groupDomainService.findByName(name);
        if (!Objects.isNull(authDataGroup)) {
            throw new ApplicationException(ErrCodeEnum.GROUP_NAME_REPEAT);
        }
        return groupDomainService.addGroup(BeanUtil.copyProperties(addGroupReq, GroupInfo.class));
    }

    @Override
    public Boolean updateGroup(UpdateGroupReq updateGroupReq) {
        String name = updateGroupReq.getName();
        Long id = updateGroupReq.getId();
        GroupInfo authDataGroup = groupDomainService.findByName(name);
        if (Objects.isNull(authDataGroup) || (!Objects.isNull(authDataGroup) && name.equals(authDataGroup.getName()) && id.equals(authDataGroup.getId()))) {
            return groupDomainService.updateGroup(BeanUtil.copyProperties(updateGroupReq, GroupInfo.class));
        }
        throw new ApplicationException(ErrCodeEnum.GROUP_NAME_REPEAT);
    }

    @Override
    public Boolean deleteGroup(Long id) {
        List<UserGroup> authDataUserGroups = userGroupDomainService.findByGroupId(id);
        if (!CollectionUtils.isEmpty(authDataUserGroups))
            throw new ApplicationException(ErrCodeEnum.GROUP_BINDING_USER);
        return groupDomainService.deleteGroup(id);
    }

    @Override
    public Page<GroupDTO> list(SearchGroupReq searchGroupReq) {
        String name = searchGroupReq.getName();
        Long pageNo = searchGroupReq.getPageNo();
        Long pageSize = searchGroupReq.getPageSize();
        Page<GroupInfo> authDataGroupPage = groupDomainService.list(name, pageNo, pageSize);
        Page<GroupDTO> result = new Page<>();
        BeanUtil.copyProperties(authDataGroupPage, result);
        List<GroupDTO> authDataGroupDTOS = BeanUtil.copyToList(authDataGroupPage.getRecords(), GroupDTO.class);
        authDataGroupDTOS.forEach(authDataGroupDTO -> authDataGroupDTO.setUserCount(userGroupDomainService.userCount(authDataGroupDTO.getId())));
        result.setRecords(authDataGroupDTOS);
        return result;
    }

    @Override
    public Page<FrameElement> listFrameElements(GroupUserReq req) {
        Long groupId = req.getGroupId();
        Long pageNo = req.getPageNo();
        Long pageSize = req.getPageSize();
        List<FrameElement> frameElements = Lists.newArrayList();
        Page<FrameElement> frameElementPage = new Page<>();
        if (!req.isFlatUser()) {
            Page<UserGroup> userGroupPage = userGroupDomainService.groupUserList(groupId, pageNo, pageSize);
            addDeptInfosIntoPage(userGroupPage, frameElements);
            addUserInfosIntoPage(userGroupPage, frameElements);

            BeanUtil.copyProperties(userGroupPage, frameElementPage);
            frameElementPage.setRecords(frameElements);
        } else {
            Page<UserInfo> userInfoPage = userGroupDomainService.flatUserList(groupId, pageNo, pageSize);

            BeanUtil.copyProperties(userInfoPage, frameElementPage);
            frameElementPage.setRecords(userInfo2FrameElement(userInfoPage.getRecords()));
        }
        return frameElementPage;
    }

    private List<FrameElement> userInfo2FrameElement(List<UserInfo> userInfos) {
        List<FrameElement> userElements = BeanUtil.copyToList(userInfos, FrameElement.class);
        userElements.forEach(userElement -> userElement.setElementType(FrameElementTypeEnums.USER));
        return userElements;
    }

    private void addUserInfosIntoPage(Page<UserGroup> userGroupPage, List<FrameElement> frameElements) {
        List<UserInfo> userInfos = userGroupPage.getRecords().stream().map(UserGroup::getUserId).filter(Objects::nonNull)
                .distinct()
                .collect(Collectors.collectingAndThen(Collectors.toList(), userInfoDomainService::getUserListByIds));
        frameElements.addAll(userInfo2FrameElement(userInfos));
    }

    private void addDeptInfosIntoPage(Page<UserGroup> userGroupPage, List<FrameElement> frameElements) {
        List<FrameElement> deptInfos = userGroupPage.getRecords().stream().map(UserGroup::getDeptId).filter(Objects::nonNull)
                .distinct()
                .collect(Collectors.collectingAndThen(Collectors.toList(), departmentInfoAppService::treeFrameByDeptIds));
        frameElements.addAll(BeanUtil.copyToList(deptInfos, FrameElement.class));
    }

    @Override
    public GroupDTO getGroupById(Long id) {
        GroupDTO groupDTO = Optional.ofNullable(id)
                .map(groupDomainService::findById)
                .map(groupInfo -> BeanUtil.copyProperties(groupInfo, GroupDTO.class))
                .orElse(null);
        if (Objects.isNull(groupDTO))
            return null;
        //查询用户组成员数
        groupDTO.setUserCount(userGroupDomainService.groupUserCount(id));
        return groupDTO;
    }

    @Override
    public Page<UserInfoDTO> listGroupUsers(GroupUserReq groupUserReq) {
        Long groupId = groupUserReq.getGroupId();
        Long pageNo = groupUserReq.getPageNo();
        Long pageSize = groupUserReq.getPageSize();
        Page<UserGroup> userGroupPage = userGroupDomainService.groupUserList(groupId, pageNo, pageSize);
        List<UserGroup> authDataUserGroupList = userGroupPage.getRecords();
        Page<UserInfoDTO> result = new Page<>();
        BeanUtil.copyProperties(authDataUserGroupList, result);
        List<Long> userIds = authDataUserGroupList.stream().map(UserGroup::getUserId).collect(Collectors.toList());
        List<UserInfo> userInfos = userInfoDomainService.getUserInfoByIds(userIds);
        result.setRecords(BeanUtil.copyToList(userInfos, UserInfoDTO.class));
        return result;
    }

    @Override
    public Boolean editGroupUsers(List<EditUserGroupReq> reqs) {
        if (CollectionUtils.isEmpty(reqs)) {
            return false;
        }
        reqs.forEach(item -> {
            Long groupId = item.getGroupId();
            List<Long> userIdList = item.getUserIds();
            //查询数据库中的数据
            List<UserGroup> authDataUserGroups = userGroupDomainService.findByGroupId(groupId);
            List<Long> dbUserIdList = authDataUserGroups.stream().map(UserGroup::getUserId).filter(Objects::nonNull).collect(Collectors.toList());
            List<Long> addUserIds = (List<Long>) CollectionUtil.subtract(userIdList, dbUserIdList);
            List<Long> delUserIds = (List<Long>) CollectionUtil.subtract(dbUserIdList, userIdList);
            userGroupDomainService.addUsers(groupId, addUserIds);
            userGroupDomainService.delUsers(groupId, delUserIds);
        });
        return true;
    }

    @Override
    public List<FrameElement> treeGroup() {
        List<FrameElement> frameGroups = getFrameGroups();
        frameGroups.forEach(item -> {
            item.setElementType(FrameElementTypeEnums.GROUP);
            if (Objects.isNull(item.getChildren())) {
                item.setChildren(Lists.newArrayList());
            }
            item.getChildren().addAll(getDepartments(item.getId()));
            item.getChildren().addAll(getUsers(item.getId()));
        });
        return frameGroups;
    }

    @Override
    public Boolean editGroupDepartments(List<EditDeptGroupReq> reqs) {
        if (CollectionUtils.isEmpty(reqs)) {
            return false;
        }
        reqs.forEach(item -> {
            Long groupId = item.getGroupId();
            List<Long> deptIdList = item.getDeptIds();
            //查询数据库中的数据
            List<UserGroup> authDataDeptGroups = userGroupDomainService.findByGroupId(groupId);
            List<Long> dbDeptIdList = authDataDeptGroups.stream().map(UserGroup::getDeptId).filter(Objects::nonNull).collect(Collectors.toList());
            List<Long> addDeptIds = (List<Long>) CollectionUtil.subtract(deptIdList, dbDeptIdList);
            List<Long> delDeptIds = (List<Long>) CollectionUtil.subtract(dbDeptIdList, deptIdList);
            userGroupDomainService.addDepartments(groupId, addDeptIds);
            userGroupDomainService.delDepartments(groupId, delDeptIds);
        });
        return true;
    }

    @Override
    public Boolean addGroupUsers(EditUserGroupReq req) {
        if (Objects.isNull(req)) {
            return false;
        }
        userGroupDomainService.addUsers(req.getGroupId(), req.getUserIds());
        return true;
    }

    @Override
    public Boolean deleteGroupMembers(GroupQueryReq req) {
        Long groupId = req.getGroupId();
        List<Long> userIds = req.getUserIds();
        List<Long> deptIds = req.getDeptIds();

        if (Objects.isNull(groupId))
            return false;
        if (CollUtil.isNotEmpty(userIds))
            userGroupDomainService.delUsers(groupId, userIds);
        if (CollUtil.isNotEmpty(deptIds))
            userGroupDomainService.delDepartments(groupId, deptIds);
        return true;
    }

    private List<FrameElement> getFrameGroups() {
        Page<GroupInfo> groupList = groupDomainService.list(null, 1L, 999L);
        List<GroupInfo> groups = groupList.getRecords();
        return BeanUtil.copyToList(groups, FrameElement.class);
    }

    private List<FrameElement> getUsers(Long groupId) {
        List<UserInfo> userInfos = userGroupDomainService.getUserListByGroupList(List.of(groupId));
        List<FrameElement> frameUsers = BeanUtil.copyToList(userInfos, FrameElement.class);
        frameUsers.forEach(item -> item.setElementType(FrameElementTypeEnums.USER));
        return frameUsers;
    }

    private List<FrameElement> getDepartments(Long groupId) {
        List<DepartmentInfo> departmentListByGroupId = userGroupDomainService.getDepartmentListByGroupId(groupId);
        List<FrameElement> frameDepartments = Lists.newArrayList();
        departmentListByGroupId.forEach(item -> {
            frameDepartments.addAll(BeanUtil.copyToList(departmentInfoAppService.treeFrameByDeptId(item.getId()), FrameElement.class));
        });
        return frameDepartments;
    }


}
