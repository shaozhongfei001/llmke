package com.gientech.ragauthservice.application.service.impl;

import cn.hutool.core.bean.BeanUtil;
import cn.hutool.core.collection.CollUtil;
import cn.hutool.core.util.ArrayUtil;
import com.alibaba.excel.util.StringUtils;
import com.gientech.ragauthservice.application.remote.ArticleTypeClient;
import com.gientech.ragauthservice.application.remote.IndexClient;
import com.gientech.ragauthservice.application.remote.SearchConfigClient;
import com.gientech.ragauthservice.application.service.PrivilegeAppService;
import com.gientech.ragauthservice.domain.entity.*;
import com.gientech.ragauthservice.domain.service.*;
import com.gientech.ragauthservice.infrastructure.convertor.DeptPrivilegeConvertor;
import com.gientech.ragauthservice.infrastructure.convertor.GroupPrivilegeConvertor;
import com.gientech.ragauthservice.infrastructure.convertor.UserInfoConvertor;
import com.gientech.ragauthservice.infrastructure.convertor.UserPrivilegeConvertor;
import com.gientech.ragcommon.auth.convertor.CollaboratorConvertor;
import com.gientech.ragcommon.auth.dto.*;
import com.gientech.ragcommon.auth.enums.FrameElementTypeEnums;
import com.gientech.ragcommon.auth.enums.PrivilegeTypeEnums;
import com.gientech.ragcommon.auth.enums.RoleTypeEnums;
import com.gientech.ragcommon.auth.enums.TransferTypeEnums;
import com.gientech.ragcommon.auth.request.*;
import com.gientech.ragcommon.context.user.User;
import com.gientech.ragcommon.context.user.UserContext;
import com.gientech.ragcommon.global.ErrCodeEnum;
import com.gientech.ragcommon.index.dto.Collaborator;
import com.gientech.ragcommon.index.enmus.PermissionEnums;
import com.gientech.ragcommon.infrastructure.exception.ApplicationException;
import com.google.common.collect.Lists;
import com.google.common.collect.Maps;
import com.google.common.collect.Sets;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.util.CollectionUtils;

import java.util.*;
import java.util.function.Function;
import java.util.stream.Collectors;
import java.util.stream.Stream;

import static com.gientech.ragcommon.auth.enums.FrameElementTypeEnums.DEPARTMENT;

@Service
@Slf4j
public class PrivilegeAppServiceImpl implements PrivilegeAppService {

    @Autowired
    private UserPrivilegeDomainService userPrivilegeDomainService;

    @Autowired
    private GroupPrivilegeDomainService groupPrivilegeDomainService;

    @Autowired
    private DeptPrivilegeDomainService deptPrivilegeDomainService;

    @Autowired
    private GroupInfoDomainService groupInfoDomainService;

    @Autowired
    private DepartmentInfoDomainService departmentInfoDomainService;

    @Autowired
    private UserGroupDomainService userGroupDomainService;

    @Autowired
    private UserInfoDomainService userInfoDomainService;

    @Autowired
    private UserRoleDomainService userRoleDomainService;

    @Autowired
    private IndexClient indexClient;

    @Autowired
    private SearchConfigClient searchConfigClient;

    @Autowired
    private ArticleTypeClient articleTypeClient;

    @Transactional
    @Override
    public Boolean setUserPrivilege(UserPrivilegeReq userPrivilegeReq) {
        Long targetId = userPrivilegeReq.getTargetId();
        List<Long> userIds = userPrivilegeReq.getUserIds();
        Integer bizType = userPrivilegeReq.getBizType();
        userPrivilegeDomainService.delete(bizType, targetId, userIds);
        userPrivilegeDomainService.addBatch(userPrivilegeReq);
        return true;
    }

    @Transactional
    @Override
    public Boolean setUserPrivilegeWithList(List<UserPrivilegeBatchReq> userPrivilegeBatchReqs) {
        if (CollectionUtils.isEmpty(userPrivilegeBatchReqs)) {
            throw new ApplicationException(ErrCodeEnum.PARAM_LIST_EMPTY);
        }
        Integer bizType = userPrivilegeBatchReqs.get(0).getBizType();
        Long targetId = userPrivilegeBatchReqs.get(0).getTargetId();
        List<Long> userIds = userPrivilegeBatchReqs.stream().map(UserPrivilegeBatchReq::getUserId).toList();
        userPrivilegeDomainService.delete(bizType, targetId, userIds);
        userPrivilegeDomainService.addBatchWithList(UserPrivilegeConvertor.INSTANCE.req2UserPrivileges(userPrivilegeBatchReqs));
        return true;
    }

    @Override
    public Boolean setGroupPrivilege(GroupPrivilegeReq groupPrivilegeReq) {
        Long targetId = groupPrivilegeReq.getTargetId();
        List<Long> groupIds = groupPrivilegeReq.getGroupIds();
        Integer bizType = groupPrivilegeReq.getBizType();
        groupPrivilegeDomainService.delete(bizType, targetId, groupIds);
        groupPrivilegeDomainService.addBatch(groupPrivilegeReq);
        return true;
    }

    @Override
    public Boolean setGroupPrivilegeWithList(List<GroupPrivilegeBatchReq> groupPrivilegeBatchReqs) {
        if (CollectionUtils.isEmpty(groupPrivilegeBatchReqs)) {
            throw new ApplicationException(ErrCodeEnum.PARAM_LIST_EMPTY);
        }
        Integer bizType = groupPrivilegeBatchReqs.get(0).getBizType();
        Long targetId = groupPrivilegeBatchReqs.get(0).getTargetId();
        List<Long> groupIds = groupPrivilegeBatchReqs.stream().map(GroupPrivilegeBatchReq::getGroupId).toList();
        groupPrivilegeDomainService.delete(bizType, targetId, groupIds);
        groupPrivilegeDomainService.addBatchWithList(GroupPrivilegeConvertor.INSTANCE.reqs2GroupPrivileges(groupPrivilegeBatchReqs));
        return true;
    }

    @Override
    public Map<Long, PrivilegeDTO> getPermission(Integer bizType, String userName) {
        User user = UserContext.getUser();
        Long userId = Long.parseLong(user.getUserId());
        if (StringUtils.isNotBlank(userName)) {
            UserInfo userInfo = userInfoDomainService.getByUserName(userName);
            userId = userInfo.getId();
        }
        return userPrivilegeDomainService.getPermission(userId, bizType, null);
    }

    @Override
    public Boolean isPermission(Integer bizType, Long targetId) {
        User user = UserContext.getUser();
        Long userId = Long.parseLong(user.getUserId());
        Integer roleType = userRoleDomainService.getRoleType(userId);
        if (RoleTypeEnums.SUPER_ADMIN.getCode().equals(roleType)) {
            return true;
        }

        List<PrivilegeDTO> allPermissionList = getAllPermission(bizType, null, null);
        if (CollUtil.isEmpty(allPermissionList))
            return false;

        return allPermissionList.stream().anyMatch(privilegeDTO -> targetId.equals(privilegeDTO.getTargetId()));


    }

    @Override
    public List<GroupPrivilegeDTO> getGroups(Integer bizType, Long targetId) {
        List<GroupPrivilegeDTO> groupPrivilegeDTOS = null;
        List<GroupPrivilege> groupPrivilegeList = groupPrivilegeDomainService.findbyTypeAndId(bizType, targetId);
        if (!CollectionUtils.isEmpty(groupPrivilegeList)) {
            groupPrivilegeDTOS = new ArrayList<>(groupPrivilegeList.size());
            List<Long> groupIds = groupPrivilegeList.stream().map(groupPrivilege -> groupPrivilege.getGroupId()).collect(Collectors.toList());
            Map<Long, GroupInfo> groupInfoMap = groupInfoDomainService.findByIds(groupIds);
            Map<Long, UserGroup> userGroupMap = userGroupDomainService.findByIds(groupIds);
            for (GroupPrivilege groupPrivilege : groupPrivilegeList) {
                GroupPrivilegeDTO groupPrivilegeDTO = BeanUtil.copyProperties(groupPrivilege, GroupPrivilegeDTO.class);
                GroupInfo groupInfo = groupInfoMap.get(groupPrivilegeDTO.getGroupId());
                UserGroup userGroup = userGroupMap.get(groupPrivilegeDTO.getGroupId());
                groupPrivilegeDTO.setGroupName(Objects.isNull(groupInfo) ? null : groupInfo.getName());
                groupPrivilegeDTO.setUserCount(Objects.isNull(userGroup) ? 0 : userGroup.getUserCount());
                groupPrivilegeDTOS.add(groupPrivilegeDTO);
            }
        }
        return groupPrivilegeDTOS;
    }

    @Override
    public List<UserPrivilegeDTO> getUsers(Integer bizType, Long targetId) {
        List<UserPrivilegeDTO> userPrivilegeDTOS = null;
        List<UserPrivilege> userPrivilegeList = userPrivilegeDomainService.findbyTypeAndId(bizType, targetId);
        if (!CollectionUtils.isEmpty(userPrivilegeList)) {
            userPrivilegeDTOS = new ArrayList<>();
            List<Long> userIds = userPrivilegeList.stream().map(UserPrivilege::getUserId).collect(Collectors.toList());
            List<UserInfo> userInfos = userInfoDomainService.getUserInfoByIds(userIds);
            Map<Long, UserInfo> userMap = new HashMap<>();
            userInfos.forEach(userInfo -> userMap.put(userInfo.getId(), userInfo));
            for (UserPrivilege userPrivilege : userPrivilegeList) {
                UserPrivilegeDTO userPrivilegeDTO = BeanUtil.copyProperties(userPrivilege, UserPrivilegeDTO.class);
                UserInfo userInfo = userMap.get(userPrivilegeDTO.getUserId());
                userPrivilegeDTO.setUserName(Objects.isNull(userInfo) ? null : userInfo.getUserName());
                userPrivilegeDTO.setDeptName(Objects.isNull(userInfo) ? null : userInfo.getDeptName());
                userPrivilegeDTO.setUserRealname(Objects.isNull(userInfo) ? null : userInfo.getUserRealname());
                userPrivilegeDTOS.add(userPrivilegeDTO);
            }
        }
        return userPrivilegeDTOS;
    }

    @Override
    public Boolean updateGroupPermission(UpdateGroupPermissionReq groupPermissionReq) {
        UpdateGroupPermissionReq queryParam = BeanUtil.copyProperties(groupPermissionReq, UpdateGroupPermissionReq.class, "permission");
        GroupPrivilege groupPrivilege = groupPrivilegeDomainService.findbyCondtion(queryParam);
        if (Objects.isNull(groupPrivilege))
            throw new ApplicationException(ErrCodeEnum.NO_GROUP_PERMISSION);
        groupPrivilege.setPermission(groupPermissionReq.getPermission());
        return groupPrivilegeDomainService.updateById(groupPrivilege);
    }

    @Override
    public Boolean updateUserPermission(UpdateUserPermissionReq userPermissionReq) {
        UpdateUserPermissionReq queryParam = BeanUtil.copyProperties(userPermissionReq, UpdateUserPermissionReq.class, "permission");
        UserPrivilege userPrivilege = userPrivilegeDomainService.findbyCondtion(queryParam);
        if (Objects.isNull(userPrivilege))
            throw new ApplicationException(ErrCodeEnum.NO_USER_PERMISSION);
        userPrivilege.setPermission(userPermissionReq.getPermission());
        return userPrivilegeDomainService.updateById(userPrivilege);
    }

    @Override
    public Boolean deleteGroupPermission(Long id) {
        if (Objects.isNull(id))
            return false;
        return groupPrivilegeDomainService.deleteById(id);
    }

    @Override
    public Boolean deleteUserPermission(Long id) {
        if (Objects.isNull(id))
            return false;
        return userPrivilegeDomainService.deleteById(id);
    }

    @Override
    public Boolean setDeptPrivilege(DeptPrivilegeReq deptPermissionReq) {
        Long targetId = deptPermissionReq.getTargetId();
        List<Long> deptIds = deptPermissionReq.getDeptIds();
        Integer bizType = deptPermissionReq.getBizType();
        deptPrivilegeDomainService.delete(bizType, targetId, deptIds);

        List<Long> availableDeptIds = deptIds.stream().filter(deptId -> Objects.nonNull(departmentInfoDomainService.findById(deptId))).toList();
        List<Long> unavailableDeptIds = CollUtil.subtractToList(deptIds, availableDeptIds);

        if (CollUtil.isNotEmpty(availableDeptIds)) {
            deptPermissionReq.setDeptIds(availableDeptIds);
            deptPrivilegeDomainService.addBatch(deptPermissionReq);
        }
        if (CollUtil.isNotEmpty(unavailableDeptIds))
            log.error("setDeptPrivilege.unavailableDeptIds:{}", unavailableDeptIds);
        return true;
    }

    @Override
    public Boolean setDeptPrivilegeWithList(List<DeptPrivilegeBatchReq> deptPrivilegeBatchReqs) {
        if (CollectionUtils.isEmpty(deptPrivilegeBatchReqs)) {
            throw new ApplicationException(ErrCodeEnum.PARAM_LIST_EMPTY);
        }
        Integer bizType = deptPrivilegeBatchReqs.get(0).getBizType();
        Long targetId = deptPrivilegeBatchReqs.get(0).getTargetId();
        List<Long> deptIds = deptPrivilegeBatchReqs.stream().map(DeptPrivilegeBatchReq::getDeptId).toList();
        deptPrivilegeDomainService.delete(bizType, targetId, deptIds);
        deptPrivilegeDomainService.addBatchWithList(DeptPrivilegeConvertor.INSTANCE.reqs2DeptPrivileges(deptPrivilegeBatchReqs));
        return true;
    }

    @Override
    public Boolean updateCurrentPermissionByBizType(UpdatePermissionReq req) {
        Integer bizType = req.getBizType().getCode();
        Long targetId = req.getTargetId();
        Integer targetPermission = req.getTargetPermission().getCode();
        Integer currentPermission = req.getCurrentPermission().getCode();

        if (Objects.nonNull(req.getElementId()) && Objects.nonNull(req.getElementType())) {
            Long elementId = req.getElementId();
            switch (req.getElementType()) {
                case DEPARTMENT:
                    updateDeptPermission(bizType, targetId, currentPermission, targetPermission, elementId);
                    break;
                case GROUP:
                    updateGroupPermission(bizType, targetId, currentPermission, targetPermission, elementId);
                    break;
                case USER:
                    updateUserPermission(bizType, targetId, currentPermission, targetPermission, elementId);
                    break;
            }
        } else {
            updateDeptPermission(bizType, targetId, currentPermission, targetPermission, null);

            updateGroupPermission(bizType, targetId, currentPermission, targetPermission, null);

            updateUserPermission(bizType, targetId, currentPermission, targetPermission, null);
        }


        return true;
    }

    private void updateDeptPermission(Integer bizType, Long targetId, Integer currentPermission, Integer targetPermission, Long elementId) {
        DeptPrivilege deptPrivilegeReq = new DeptPrivilege();
        deptPrivilegeReq.setBizType(bizType);
        deptPrivilegeReq.setTargetId(targetId);
        deptPrivilegeReq.setPermission(currentPermission);
        List<DeptPrivilege> deptPrivileges = deptPrivilegeDomainService.list(deptPrivilegeReq);
        deptPrivilegeDomainService.updatePermissionBatch(deptPrivileges, targetPermission, elementId);
    }

    private void updateGroupPermission(Integer bizType, Long targetId, Integer currentPermission, Integer targetPermission, Long elementId) {
        GroupPrivilege groupPrivilegeReq = new GroupPrivilege();
        groupPrivilegeReq.setBizType(bizType);
        groupPrivilegeReq.setTargetId(targetId);
        groupPrivilegeReq.setPermission(currentPermission);
        List<GroupPrivilege> groupPrivileges = groupPrivilegeDomainService.list(groupPrivilegeReq);
        groupPrivilegeDomainService.updatePermissionBatch(groupPrivileges, targetPermission, elementId);
    }

    private void updateUserPermission(Integer bizType, Long targetId, Integer currentPermission, Integer targetPermission, Long elementId) {
        UserPrivilege userPrivilegeReq = new UserPrivilege();
        userPrivilegeReq.setBizType(bizType);
        userPrivilegeReq.setTargetId(targetId);
        userPrivilegeReq.setPermission(currentPermission);
        List<UserPrivilege> userPrivileges = userPrivilegeDomainService.list(userPrivilegeReq);
        userPrivilegeDomainService.updatePermissionBatch(userPrivileges, targetPermission, elementId);
    }

    @Override
    public List<DeptPrivilegeDTO> getDeptList(Integer bizType, Long targetId) {
        // 获取部门-数据权限关联列表
        List<DeptPrivilege> deptPrivilegeList = deptPrivilegeDomainService.findByTypeAndId(bizType, targetId);
        if (CollUtil.isEmpty(deptPrivilegeList))
            return Lists.newArrayList();

        // 获取所有部门及其子部门的ID
        Set<Long> allDeptIds = getAllDeptIds(deptPrivilegeList);

        // 获取所有部门及其子部门的基本信息
        Map<Long, DepartmentInfo> departmentInfoMap = getDepartmentInfoMap(allDeptIds);

        // 获取所有部门及其子部门的成员数量信息
        Map<Long, Long> userCountInDeptMap = getUserCountInDeptMap(allDeptIds);

        // 构建 DeptPrivilegeDTO 对象
        Map<Long, DeptPrivilegeDTO> deptPrivilegeDTOMap = buildDeptPrivilegeDTOMap(bizType, targetId, deptPrivilegeList, allDeptIds, departmentInfoMap, userCountInDeptMap);

        // 设置默认权限
        setDefaultPermissions(departmentInfoMap, deptPrivilegeDTOMap);

        // 构建树结构
        ArrayList<DeptPrivilegeDTO> tree = buildTree(deptPrivilegeDTOMap, departmentInfoMap);

        // 计算每个部门及其子部门的成员总数
        calculateTotalUserCount(tree);
        return tree;

    }

    @Override
    public Boolean updateDeptPermission(UpdateDeptPermissionReq deptPermissionReq) {
        UpdateDeptPermissionReq queryParam = BeanUtil.copyProperties(deptPermissionReq, UpdateDeptPermissionReq.class, "permission");
        DeptPrivilege deptPrivilege = deptPrivilegeDomainService.findByCondition(queryParam);
        if (Objects.isNull(deptPrivilege))
            throw new ApplicationException(ErrCodeEnum.NO_DEPT_PERMISSION);
        deptPrivilege.setPermission(deptPermissionReq.getPermission());
        return deptPrivilegeDomainService.updateById(deptPrivilege);
    }

    @Override
    public Boolean deleteDeptPermission(Long id) {
        if (Objects.isNull(id))
            return false;
        return deptPrivilegeDomainService.deleteById(id);
    }

    @Override
    public PublicAccessPrivilegeDTO getPublicAccess(Integer bizType, Long targetId) {
        // 创建查询参数,userId=-1代表所有人可访问
        UpdateUserPermissionReq param = new UpdateUserPermissionReq();
        param.setBizType(bizType);
        param.setTargetId(targetId);
        param.setUserId(-1L);

        // 查询公共权限
        UserPrivilege userPrivilege = userPrivilegeDomainService.findbyCondtion(param);

        // 创建并返回公共访问权限DTO
        PublicAccessPrivilegeDTO publicAccessPrivilegeDTO = new PublicAccessPrivilegeDTO();
        publicAccessPrivilegeDTO.setIsPublicAccess(Objects.nonNull(userPrivilege));
        if (Objects.nonNull(userPrivilege)) {
            BeanUtil.copyProperties(userPrivilege, publicAccessPrivilegeDTO);
        }

        return publicAccessPrivilegeDTO;
    }

    @Override
    public List<Collaborator> getUserListGroupByPermission(Long kbId, Integer bizType, Long targetId) {

        List<Collaborator> collaborators = Lists.newArrayList();


        List<UserPrivilege> userPrivilegeList = userPrivilegeDomainService.findbyTypeAndId(bizType, targetId);
        List<UserPrivilege> kbUserPrivilegeList = userPrivilegeDomainService.findbyTypeAndId(PrivilegeTypeEnums.KNOWLEDGE_BASE.getCode(), kbId);
        List<GroupPrivilege> groupPrivilegeList = groupPrivilegeDomainService.findbyTypeAndId(PrivilegeTypeEnums.KNOWLEDGE_BASE.getCode(), kbId);
        List<DeptPrivilege> deptPrivilegeList = deptPrivilegeDomainService.findByTypeAndId(PrivilegeTypeEnums.KNOWLEDGE_BASE.getCode(), kbId);


        TreeMap<Integer, List<UserPrivilege>> userPermissionGroup = kbUserPrivilegeList.stream().collect(Collectors.groupingBy(UserPrivilege::getPermission, TreeMap::new, Collectors.toList()));
        TreeMap<Integer, List<GroupPrivilege>> groupPermissionGroup = groupPrivilegeList.stream().collect(Collectors.groupingBy(GroupPrivilege::getPermission, TreeMap::new, Collectors.toList()));
        TreeMap<Integer, List<DeptPrivilege>> deptPermissionGroup = deptPrivilegeList.stream().collect(Collectors.groupingBy(DeptPrivilege::getPermission, TreeMap::new, Collectors.toList()));

        getEveryonePermission(userPrivilegeList, collaborators);

//        collaborators.add(collectByPermission(userPermissionGroup,groupPermissionGroup,deptPermissionGroup, PermissionEnums.NO_PERMISSION.getCode(),"无权限"));

        collaborators.add(collectByPermission(userPermissionGroup, groupPermissionGroup, deptPermissionGroup, PermissionEnums.READ.getCode(), "可阅读成员"));

        collaborators.add(collectByPermission(userPermissionGroup, groupPermissionGroup, deptPermissionGroup, PermissionEnums.READ_WRITE.getCode(), "可编辑成员"));

        collaborators.add(collectByPermission(userPermissionGroup, groupPermissionGroup, deptPermissionGroup, PermissionEnums.ALL.getCode(), "可管理成员"));

        List<AllPrivilegeDTO> allList = getAllList(bizType, targetId).stream().filter(item -> (Objects.isNull(item.getUserId()) || !item.getUserId().equals(-1L))).toList();

        collaborators.addAll(CollaboratorConvertor.INSTANCE.allPrivilege2Collaborators(allList));

        return collaborators;
    }

    private Collaborator collectByPermission(TreeMap<Integer, List<UserPrivilege>> userPermissionGroup, TreeMap<Integer, List<GroupPrivilege>> groupPermissionGroup, TreeMap<Integer, List<DeptPrivilege>> deptPermissionGroup, Integer permission, String userType) {
        Collaborator collaborator = Collaborator.builder().userType(userType).build();
        List<UserPrivilege> userPrivilegeList = CollectionUtils.isEmpty(userPermissionGroup.get(permission)) ? Lists.newArrayList() : userPermissionGroup.get(permission);
        List<UserPrivilege> noPrivilegeList = CollectionUtils.isEmpty(userPermissionGroup.get(PermissionEnums.NO_PERMISSION.getCode())) ? Lists.newArrayList() : userPermissionGroup.get(PermissionEnums.NO_PERMISSION.getCode());
        List<GroupPrivilege> groupPrivilegeList = CollectionUtils.isEmpty(groupPermissionGroup.get(permission)) ? Lists.newArrayList() : groupPermissionGroup.get(permission);
        List<DeptPrivilege> deptPrivilegeList = CollectionUtils.isEmpty(deptPermissionGroup.get(permission)) ? Lists.newArrayList() : deptPermissionGroup.get(permission);

        List<Long> userIds = userPrivilegeList.stream().map(UserPrivilege::getUserId).collect(Collectors.toCollection(ArrayList::new));
        List<Long> noPermissionUserIds = noPrivilegeList.stream().map(UserPrivilege::getUserId).collect(Collectors.toCollection(ArrayList::new));
        collaborator.setUsers(new HashSet<>(UserInfoConvertor.INSTANCE.userInfoS2SimpleUsers(userInfoDomainService.getUserInfoByIds(userIds))));


        List<Long> groupIds = groupPrivilegeList.stream().map(GroupPrivilege::getGroupId).collect(Collectors.toCollection(ArrayList::new));
        List<UserInfo> userListByGroupList = userGroupDomainService.getUserListByGroupList(groupIds);
        collaborator.getUsers().addAll(BeanUtil.copyToList(userListByGroupList, SimpleUserDTO.class));


        ArrayList<Long> deptIds = deptPrivilegeList.stream().map(DeptPrivilege::getDeptId).collect(Collectors.toCollection(ArrayList::new));
        collaborator.getUsers().addAll(UserInfoConvertor.INSTANCE.userInfoS2SimpleUsers(userInfoDomainService.listByDeptIds(deptIds)));

        collaborator.getUsers().removeAll(new HashSet<>(UserInfoConvertor.INSTANCE.userInfoS2SimpleUsers(userInfoDomainService.getUserInfoByIds(noPermissionUserIds))));
        collaborator.setUserCount(collaborator.getUsers().size());
        collaborator.setPermission(PermissionEnums.of(permission));
        return collaborator;
    }


    private void getEveryonePermission(List<UserPrivilege> userPrivilegeList, List<Collaborator> collaborators) {
        Collaborator allPrivilege = Collaborator.builder().userType("所有人").build();
        Optional<UserPrivilege> all = userPrivilegeList.stream().filter(up -> up.getUserId() < 0).findFirst();
        all.ifPresent(userPrivilege -> {
            allPrivilege.setPermission(PermissionEnums.of(userPrivilege.getPermission()));
            allPrivilege.setUserId(userPrivilege.getUserId());
            allPrivilege.setId(userPrivilege.getId());
        });
        if (all.isPresent()) {
            collaborators.add(allPrivilege);
        }
    }

    @Override
    public List<PrivilegeDTO> getAllPermission(Integer bizType, String userName, Long[] targetIds) {
        // 获取用户ID，若提供了用户名则使用对应的用户ID,否则使用当前用户ID
        Long userId = getUserId(userName);

        List<Long> targetIdList = ArrayUtil.isEmpty(targetIds) ? List.of() : Arrays.asList(targetIds);

        // 获取公共权限列表
        List<PrivilegeDTO> publicPrivilegeList = getPublicPrivileges(bizType, targetIdList);

        // 获取部门权限列表
        List<PrivilegeDTO> deptPrivilegeList = getDeptPrivileges(bizType, userId, targetIdList);

        // 获取用户组权限列表
        List<PrivilegeDTO> groupPrivilegeList = getGroupPrivileges(bizType, userId, targetIdList);

        // 获取用户权限列表
        List<PrivilegeDTO> userPrivilegeList = getUserPrivileges(bizType, userId, targetIdList);

        // 合并所有权限列表，若存在相同的数据,取权限较大的数据
        return mergePrivileges(publicPrivilegeList, deptPrivilegeList, groupPrivilegeList, userPrivilegeList);
    }


    @Override
    public List<PrivilegeDTO> getPermissionByTargetId(Integer bizType, Long[] targetIds) {
        return getAllPermission(bizType, null, targetIds);
    }

    @Override
    public List<AllPrivilegeDTO> getAllList(Integer bizType, Long targetId) {
        // 获取数据权限下的所有人和用户
        List<AllPrivilegeDTO> userPrivilegeList = queryUserAllPrivilegeList(bizType, targetId);
        // 获取数据权限下的部门
        List<AllPrivilegeDTO> deptPrivilegeList = queryDeptPrivilegeList(bizType, targetId);
        // 获取数据权限下的用户组
        List<AllPrivilegeDTO> groupPrivilegeList = queryGroupPrivilegeList(bizType, targetId);

        List<AllPrivilegeDTO> allPrivilegeDTOList = new ArrayList<>();
        allPrivilegeDTOList.addAll(userPrivilegeList);
        allPrivilegeDTOList.addAll(deptPrivilegeList);
        allPrivilegeDTOList.addAll(groupPrivilegeList);

        return allPrivilegeDTOList;
    }

    private List<AllPrivilegeDTO> queryGroupPrivilegeList(Integer bizType, Long targetId) {
        // 获取部门-数据权限关联列表
        List<GroupPrivilege> groupPrivilegeList = groupPrivilegeDomainService.findbyTypeAndId(bizType, targetId);
        if (CollUtil.isEmpty(groupPrivilegeList)) {
            return Lists.newArrayList();
        }

        // 收集所有需要查询的组ID
        List<Long> groupIds = groupPrivilegeList.stream()
                .map(GroupPrivilege::getGroupId)
                .collect(Collectors.toList());

        // 批量查询组信息
        Map<Long, GroupInfo> groupInfoMap = groupInfoDomainService.findByIds(groupIds);

        // 转换为 AllPrivilegeDTO
        Map<String, AllPrivilegeDTO> dtoMap = groupPrivilegeList.stream()
                .map(groupPrivilege -> {
                    AllPrivilegeDTO allPrivilegeDTO = BeanUtil.copyProperties(groupPrivilege, AllPrivilegeDTO.class);
                    GroupInfo groupInfo = groupInfoMap.get(groupPrivilege.getGroupId());
                    if (Objects.nonNull(groupInfo)) {
                        allPrivilegeDTO.setGroupName(groupInfo.getName());
                        allPrivilegeDTO.setElementType(FrameElementTypeEnums.GROUP.getType());
                    }
                    return allPrivilegeDTO;
                })
                .filter(allPrivilegeDTO -> Objects.nonNull(allPrivilegeDTO.getGroupName())) // 过滤掉没有组信息的记录
                .collect(Collectors.toMap(
                        allPrivilegeDTO -> allPrivilegeDTO.getElementType() + "-" + allPrivilegeDTO.getBizType() + "-" + allPrivilegeDTO.getTargetId() + "-" + allPrivilegeDTO.getGroupId(),
                        Function.identity(),
                        (existing, replacement) -> existing.getPermission() >= replacement.getPermission() ? existing : replacement));

        return Lists.newArrayList(dtoMap.values());
    }


    private List<AllPrivilegeDTO> queryDeptPrivilegeList(Integer bizType, Long targetId) {
        // 获取部门-数据权限关联列表
        List<DeptPrivilege> deptPrivilegeList = deptPrivilegeDomainService.findByTypeAndId(bizType, targetId);
        if (CollUtil.isEmpty(deptPrivilegeList)) {
            return Lists.newArrayList();
        }

        // 收集所有需要查询的部门ID
        List<Long> deptIds = deptPrivilegeList.stream()
                .map(DeptPrivilege::getDeptId)
                .collect(Collectors.toList());

        // 批量查询部门信息
        Map<Long, DepartmentInfo> departmentInfoMap = departmentInfoDomainService.listByIds(deptIds).stream()
                .collect(Collectors.toMap(DepartmentInfo::getId, Function.identity()));

        // 转换为 AllPrivilegeDTO 列表
        Map<String, AllPrivilegeDTO> dtoMap = deptPrivilegeList.stream()
                .map(deptPrivilege -> {
                    AllPrivilegeDTO allPrivilegeDTO = BeanUtil.copyProperties(deptPrivilege, AllPrivilegeDTO.class);
                    DepartmentInfo departmentInfo = departmentInfoMap.get(deptPrivilege.getDeptId());
                    if (Objects.nonNull(departmentInfo)) {
                        allPrivilegeDTO.setDeptName(departmentInfo.getName());
                        allPrivilegeDTO.setElementType(DEPARTMENT.getType());
                    }
                    return allPrivilegeDTO;
                })
                .filter(allPrivilegeDTO -> Objects.nonNull(allPrivilegeDTO.getDeptName())) // 过滤掉没有部门信息的记录
                .collect(Collectors.toMap(
                        allPrivilegeDTO -> allPrivilegeDTO.getElementType() + "-" + allPrivilegeDTO.getBizType() + "-" + allPrivilegeDTO.getTargetId() + "-" + allPrivilegeDTO.getDeptId(),
                        Function.identity(),
                        (existing, replacement) -> existing.getPermission() >= replacement.getPermission() ? existing : replacement));

        return Lists.newArrayList(dtoMap.values());
    }

    /**
     * 获取数据权限下的所有人和用户
     *
     * @param bizType
     * @param targetId
     * @return
     */
    private List<AllPrivilegeDTO> queryUserAllPrivilegeList(Integer bizType, Long targetId) {
        ArrayList<AllPrivilegeDTO> results = Lists.newArrayList();

        // 资源创建者
        AllPrivilegeDTO creatorAllPrivilegeDTO = assembleCreatorPrivilegeDTO(bizType, targetId);
        if (Objects.nonNull(creatorAllPrivilegeDTO)) {
            results.add(creatorAllPrivilegeDTO);
        }

        // 数据权限下用户和所有人
        List<UserPrivilegeDTO> userPrivilegeDTOS = getUsers(bizType, targetId);
        if (CollUtil.isEmpty(userPrivilegeDTOS))
            return results;

        List<AllPrivilegeDTO> privilegeDTOList = userPrivilegeDTOS.stream()
                .map(userPrivilegeDTO -> {
                    AllPrivilegeDTO allPrivilegeDTO = BeanUtil.copyProperties(userPrivilegeDTO, AllPrivilegeDTO.class);
                    allPrivilegeDTO.setElementType(FrameElementTypeEnums.USER.getType());
                    allPrivilegeDTO.setCreator(Boolean.FALSE);
                    return allPrivilegeDTO;
                }).collect(Collectors.toList());

        results.addAll(privilegeDTOList);

        // 去重
        Map<String, AllPrivilegeDTO> dtoMap = results.stream().collect(Collectors.toMap(
                allPrivilegeDTO -> allPrivilegeDTO.getElementType() + "-" + allPrivilegeDTO.getBizType() + "-" + allPrivilegeDTO.getTargetId() + "-" + allPrivilegeDTO.getUserId(),
                Function.identity(),
                (existing, replacement) -> existing.getPermission() >= replacement.getPermission() ? existing : replacement));

        // 根据用户ID排序
        return Lists.newArrayList(dtoMap.values()).stream()
                .sorted(Comparator.comparing(AllPrivilegeDTO::getUserId))
                .collect(Collectors.toList());
    }

    private AllPrivilegeDTO assembleCreatorPrivilegeDTO(Integer bizType, Long targetId) {
        // 获取资源创建者用户信息
        UserInfo creatorInfo = Optional.ofNullable(queryResourceCreator(bizType, targetId))
                .map(creator -> userInfoDomainService.getByUserName(creator))
                .orElse(null);
        if (Objects.isNull(creatorInfo))
            return null;

        return AllPrivilegeDTO.builder()
                .elementType(FrameElementTypeEnums.USER.getType())
                .bizType(bizType)
                .targetId(targetId)
                .deptName(creatorInfo.getDeptName())
                .permission(PermissionEnums.ALL.getCode())
                .userId(creatorInfo.getId())
                .userName(creatorInfo.getUserName())
                .userRealname(creatorInfo.getUserRealname())
                .creator(Boolean.TRUE)
                .build();
    }

    /**
     * 查询资源创建者
     *
     * @param bizType
     * @param targetId
     * @return
     */
    private String queryResourceCreator(Integer bizType, Long targetId) {
        return switch (PrivilegeTypeEnums.getEnumByCode(bizType)) {
            case KNOWLEDGE_BASE -> indexClient.queryKbCreator(targetId).getData();
            case INDEX_CONF -> searchConfigClient.querySearchConfigCreator(targetId).getData();
            case MODEL -> indexClient.queryModelCreator(targetId).getData();
            case ARTICLE_TEMPLATE -> articleTypeClient.queryCreator(targetId).getData();
            case KNOWLEDGE_BASE_FILE, FAQ_FILE, FAQ_EXTRACT_FILE -> indexClient.queryKbFileCreator(targetId).getData();
            case FOLDER, FAQ_FOLDER, FAQ_EXTRACT_FOLDER -> indexClient.queryFolderCreator(targetId).getData();
            case FAQ -> null;
            case DATABASE -> indexClient.queryDatabaseCreator(targetId).getData();
        };
    }


    /**
     * 获取用户ID，若提供了用户名则使用对应的用户ID,否则使用当前用户ID
     *
     * @param userName 用户名
     * @return 用户ID
     */
    private Long getUserId(String userName) {
        Long userId = Long.parseLong(UserContext.getUser().getUserId());
        if (StringUtils.isNotBlank(userName)) {
            UserInfo userInfo = userInfoDomainService.getByUserName(userName);
            if (Objects.nonNull(userInfo))
                userId = userInfo.getId();
        }
        return userId;
    }

    /**
     * 获取公共权限列表（userId=-1表示所有人可以访问）
     *
     * @param bizType 业务类型
     * @return 公共权限列表
     */
    private List<PrivilegeDTO> getPublicPrivileges(Integer bizType, List<Long> targetIds) {
        UserPrivilege userQueryParam = new UserPrivilege();
        userQueryParam.setBizType(bizType);
        userQueryParam.setTargetIds(targetIds);
        userQueryParam.setUserId(-1L);
        return BeanUtil.copyToList(userPrivilegeDomainService.list(userQueryParam), PrivilegeDTO.class);
    }


    /**
     * 获取部门以及所有父部门的权限列表
     *
     * @param bizType 业务类型
     * @param userId  用户ID
     * @return 部门权限列表
     */
    private List<PrivilegeDTO> getDeptPrivileges(Integer bizType, Long userId, List<Long> targetIds) {
        List<DeptPrivilege> deptPrivilegeList;
        Map<String, PrivilegeDTO> privilegeDTOMap = new HashMap<>();

        // 获取部门ID
        Long deptId = Optional.ofNullable(userInfoDomainService.getUserInfoById(userId))
                .map(UserInfo::getDeptId)
                .map(Long::valueOf)
                .orElse(null);

        // 递归查找部门及其父部门的权限信息
        while (Objects.nonNull(deptId)) {
            DepartmentInfo departmentInfo = departmentInfoDomainService.findById(Long.valueOf(deptId));
            if (Objects.isNull(departmentInfo))
                break;

            // 查询部门的权限信息
            DeptPrivilege deptQueryParam = new DeptPrivilege();
            deptQueryParam.setBizType(bizType);
            deptQueryParam.setDeptId(deptId);
            deptQueryParam.setTargetIds(targetIds);
            deptPrivilegeList = deptPrivilegeDomainService.list(deptQueryParam);
            List<PrivilegeDTO> privilegeDTOS = BeanUtil.copyToList(deptPrivilegeList, PrivilegeDTO.class);

            // 权限合并,优先级为子部门 > 父部门
            mergePrivilegesIntoMap(privilegeDTOMap, privilegeDTOS);

            // 获取父部门ID
            deptId = departmentInfo.getParentId();
        }
        return CollUtil.isEmpty(privilegeDTOMap.values()) ? Lists.newArrayList() : Lists.newArrayList(privilegeDTOMap.values());
    }

    /**
     * 获取用户组权限列表
     *
     * @param bizType
     * @param userId
     * @return
     */
    private List<PrivilegeDTO> getGroupPrivileges(Integer bizType, Long userId, List<Long> targetIds) {
        // 用户组用户权限
        List<PrivilegeDTO> groupUserPrivilegeDTOS = getGroupUserPrivilegeDTOS(bizType, userId, targetIds);

        // 用户组部门权限
        List<PrivilegeDTO> groupDeptPrivilegeDTOS = getGroupDeptPrivilegeDTOS(bizType, userId, targetIds);

        ArrayList<PrivilegeDTO> privilegeDTOList = new ArrayList<>();
        privilegeDTOList.addAll(groupUserPrivilegeDTOS);
        privilegeDTOList.addAll(groupDeptPrivilegeDTOS);
        return privilegeDTOList;
    }


    /**
     * 获取用户组部门的权限信息
     *
     * @param bizType
     * @param userId
     * @return
     */
    private List<PrivilegeDTO> getGroupDeptPrivilegeDTOS(Integer bizType, Long userId, List<Long> targetIds) {
        List<GroupPrivilege> groupPrivilegeList;
        Map<String, PrivilegeDTO> groupDeptPrivilegeDTOMap = new HashMap<>();

        // 部门ID
        Long deptId = Optional.ofNullable(userInfoDomainService.getUserInfoById(userId))
                .map(UserInfo::getDeptId)
                .map(Long::valueOf)
                .orElse(null);

        // 递归查找部门及其父部门所在用户组的权限信息
        while (Objects.nonNull(deptId)) {
            DepartmentInfo departmentInfo = departmentInfoDomainService.findById(Long.valueOf(deptId));
            if (Objects.isNull(departmentInfo))
                break;

            List<Long> groupIds = userGroupDomainService.listGroupIdsByDeptId(deptId);
            groupIds = Lists.newArrayList(groupInfoDomainService.findByIds(groupIds).keySet());

            groupPrivilegeList = groupPrivilegeDomainService.findByTypeAndGroupIds(bizType, groupIds, targetIds);
            List<PrivilegeDTO> privilegeDTOS = BeanUtil.copyToList(groupPrivilegeList, PrivilegeDTO.class);

            // 同级去重,若重复,取权限较大的
            privilegeDTOS = sameLevelDeduplication(privilegeDTOS);

            // 权限合并,优先级为子部门 > 父部门
            mergePrivilegesIntoMap(groupDeptPrivilegeDTOMap, privilegeDTOS);

            // 获取父部门ID
            deptId = departmentInfo.getParentId();
        }
        return CollUtil.isEmpty(groupDeptPrivilegeDTOMap.values()) ? Lists.newArrayList() : Lists.newArrayList(groupDeptPrivilegeDTOMap.values());
    }

    /**
     * 同级去重,若重复,取权限较大的
     *
     * @param privilegeDTOS
     * @return
     */
    private List<PrivilegeDTO> sameLevelDeduplication(List<PrivilegeDTO> privilegeDTOS) {
        if (CollUtil.isEmpty(privilegeDTOS))
            return Lists.newArrayList();

        Map<String, PrivilegeDTO> privilegeDTOMap = privilegeDTOS.stream()
                .collect(Collectors.toMap(
                        this::createKey,
                        Function.identity(),
                        (oldValue, newValue) -> oldValue.getPermission() >= newValue.getPermission() ? oldValue : newValue));

        return Lists.newArrayList(privilegeDTOMap.values());
    }

    /**
     * 获取用户组用户的权限信息
     *
     * @param bizType
     * @param userId
     * @return
     */
    private List<PrivilegeDTO> getGroupUserPrivilegeDTOS(Integer bizType, Long userId, List<Long> targetIds) {
        List<Long> groupIdList = userGroupDomainService.listGroupIdsByUserId(userId);
        List<PrivilegeDTO> groupUserPrivilegeDTOS = BeanUtil.copyToList(groupPrivilegeDomainService.findByTypeAndGroupIds(bizType, groupIdList, targetIds), PrivilegeDTO.class);
        return groupUserPrivilegeDTOS;
    }

    /**
     * 将权限列表合并到Map中
     *
     * @param privilegeDTOMap 权限Map
     * @param privileges      权限列表
     */
    private void mergePrivilegesIntoMap(Map<String, PrivilegeDTO> privilegeDTOMap, List<PrivilegeDTO> privileges) {
        if (CollectionUtils.isEmpty(privileges)) {
            return;
        }
        for (PrivilegeDTO privilegeDTO : privileges) {
            String key = createKey(privilegeDTO);
            if (!privilegeDTOMap.containsKey(key)) {
                privilegeDTOMap.put(key, privilegeDTO);
            }
        }
    }


    /**
     * 获取用户权限列表
     *
     * @param bizType 业务类型
     * @param userId  用户ID
     * @return 用户权限列表
     */
    private List<PrivilegeDTO> getUserPrivileges(Integer bizType, Long userId, List<Long> targetIds) {
        UserPrivilege userQueryParam = new UserPrivilege();
        userQueryParam.setBizType(bizType);
        userQueryParam.setTargetIds(targetIds);
        userQueryParam.setUserId(userId);
        return BeanUtil.copyToList(userPrivilegeDomainService.list(userQueryParam), PrivilegeDTO.class);
    }

    /**
     * 合并所有权限列表，若存在相同的数据,取权限较大的数据
     *
     * @param publicPrivilegeList 公共权限列表
     * @param deptPrivilegeList   部门权限列表
     * @param groupPrivilegeList  用户组权限列表
     * @param userPrivilegeList   用户权限列表
     * @return 合并后的权限列表
     */
    private List<PrivilegeDTO> mergePrivileges(List<PrivilegeDTO> publicPrivilegeList, List<PrivilegeDTO> deptPrivilegeList, List<PrivilegeDTO> groupPrivilegeList, List<PrivilegeDTO> userPrivilegeList) {
        Map<String, PrivilegeDTO> privilegeMap = Stream.of(publicPrivilegeList.stream(), deptPrivilegeList.stream(), groupPrivilegeList.stream(), userPrivilegeList.stream())
                .flatMap(Function.identity())
                .filter(p -> p.getPermission() > PermissionEnums.NO_PERMISSION.getCode())
                .collect(Collectors.toMap(
                        this::createKey,
                        Function.identity(),
                        (existing, replacement) -> existing.getPermission() > replacement.getPermission() ? existing : replacement
                ));

        return CollUtil.isEmpty(privilegeMap.values()) ? Lists.newArrayList() : Lists.newArrayList(privilegeMap.values());
    }


    private String createKey(PrivilegeDTO privilegeDTO) {
        return privilegeDTO.getBizType() + "_" + privilegeDTO.getTargetId();
    }


    /**
     * 计算每个部门及其子部门的成员总数
     *
     * @param tree
     */
    private void calculateTotalUserCount(List<DeptPrivilegeDTO> tree) {
        if (CollUtil.isEmpty(tree))
            return;

        tree.forEach(deptPrivilegeDTO -> calculateTotalUserCount(deptPrivilegeDTO));
    }


    /**
     * 构建 DeptPrivilegeDTO 对象
     *
     * @param bizType
     * @param targetId
     * @param deptPrivilegeList
     * @param allDeptIds
     * @param departmentInfoMap
     * @param userCountInDeptMap
     * @return
     */
    private Map<Long, DeptPrivilegeDTO> buildDeptPrivilegeDTOMap(Integer bizType, Long targetId, List<DeptPrivilege> deptPrivilegeList, Set<Long> allDeptIds, Map<Long, DepartmentInfo> departmentInfoMap, Map<Long, Long> userCountInDeptMap) {
        Map<Long, DeptPrivilegeDTO> deptPrivilegeDTOMap = Maps.newHashMap();
        Map<Long, DeptPrivilege> deptPrivilegeMap = deptPrivilegeList.stream()
                .collect(Collectors.toMap(DeptPrivilege::getDeptId, Function.identity()));

        for (Long deptId : allDeptIds) {
            DepartmentInfo departmentInfo = departmentInfoMap.get(deptId);

            DeptPrivilegeDTO deptPrivilegeDTO = new DeptPrivilegeDTO();
            DeptPrivilege deptPrivilege = deptPrivilegeMap.get(deptId);
            if (deptPrivilege != null) {
                BeanUtil.copyProperties(deptPrivilege, deptPrivilegeDTO);
            }
            deptPrivilegeDTO.setBizType(bizType);
            deptPrivilegeDTO.setTargetId(targetId);
            deptPrivilegeDTO.setDeptId(departmentInfo.getId());
            deptPrivilegeDTO.setDeptName(departmentInfo.getName());
            deptPrivilegeDTO.setUserCount(userCountInDeptMap.getOrDefault(deptId, 0L));
            deptPrivilegeDTOMap.put(deptId, deptPrivilegeDTO);
        }
        return deptPrivilegeDTOMap;
    }

    /**
     * 获取所有部门及其子部门的成员数量信息
     *
     * @param allDeptIds
     * @return
     */
    private Map<Long, Long> getUserCountInDeptMap(Set<Long> allDeptIds) {
        HashMap<Long, Long> userCountInDeptMap = new HashMap<>();
        for (Long deptId : allDeptIds) {
            UserInfo userInfoParam = new UserInfo();
            userInfoParam.setDeptId(String.valueOf(deptId));
            userCountInDeptMap.put(deptId, Long.valueOf(userInfoDomainService.list(userInfoParam).size()));
        }
        return userCountInDeptMap;
    }

    /**
     * 获取所有部门及其子部门的基本信息
     *
     * @param allDeptIds
     * @return
     */
    private Map<Long, DepartmentInfo> getDepartmentInfoMap(Set<Long> allDeptIds) {
        return departmentInfoDomainService.listByIds(Lists.newArrayList(allDeptIds)).stream()
                .collect(Collectors.toMap(DepartmentInfo::getId, Function.identity()));
    }

    /**
     * 获取所有部门及其子部门的ID
     *
     * @param deptPrivilegeList
     * @return
     */
    private Set<Long> getAllDeptIds(List<DeptPrivilege> deptPrivilegeList) {
        Set<Long> allDeptIds = new HashSet<>();
        List<Long> deptIds = deptPrivilegeList.stream().map(DeptPrivilege::getDeptId).toList();

        // 保证allDeptIds中的部门都真实存在
        departmentInfoDomainService.listByIds(deptIds).stream()
                .map(DepartmentInfo::getId)
                .forEach(deptId -> {
                    allDeptIds.add(deptId);
                    allDeptIds.addAll(getAllChildDeptIds(deptId));
                });

        return allDeptIds;
    }

    /**
     * 递归获取子部门的ID信息
     *
     * @param deptId
     * @return
     */
    private Set<Long> getAllChildDeptIds(Long deptId) {
        Set<Long> childDeptIds = Sets.newHashSet();

        ListDepartmentInfoReq departmentInfoReqParam = new ListDepartmentInfoReq();
        departmentInfoReqParam.setParentId(deptId);
        departmentInfoReqParam.setPageNo(1L);
        departmentInfoReqParam.setPageSize(9999L);
        List<DepartmentInfo> directChildDeptInfos = departmentInfoDomainService.list(departmentInfoReqParam).getRecords();

        if (CollUtil.isEmpty(directChildDeptInfos))
            return childDeptIds;
        List<Long> directChildDeptIds = directChildDeptInfos.stream().map(DepartmentInfo::getId).toList();
        childDeptIds.addAll(directChildDeptIds);
        for (Long directChildDept : directChildDeptIds) {
            childDeptIds.addAll(getAllChildDeptIds(directChildDept));
        }
        return childDeptIds;
    }

    /**
     * 计算每个部门及其子部门的成员总数
     *
     * @param deptPrivilegeDTO
     */
    private void calculateTotalUserCount(DeptPrivilegeDTO deptPrivilegeDTO) {
        if (deptPrivilegeDTO.getSubDeptPrivilegeList() != null) {
            for (DeptPrivilegeDTO subDeptPrivilegeDTO : deptPrivilegeDTO.getSubDeptPrivilegeList()) {
                calculateTotalUserCount(subDeptPrivilegeDTO);
                deptPrivilegeDTO.setUserCount(deptPrivilegeDTO.getUserCount() + subDeptPrivilegeDTO.getUserCount());
            }
        }
    }

    /**
     * 设置默认权限
     *
     * @param departmentInfoMap
     * @param deptPrivilegeDTOMap
     */
    private void setDefaultPermissions(Map<Long, DepartmentInfo> departmentInfoMap, Map<Long, DeptPrivilegeDTO> deptPrivilegeDTOMap) {
        for (DeptPrivilegeDTO deptPrivilegeDTO : deptPrivilegeDTOMap.values()) {
            if (deptPrivilegeDTO.getPermission() == null) {
                Long deptId = deptPrivilegeDTO.getDeptId();
                Integer permission = findNonEmptyPermission(departmentInfoMap, deptPrivilegeDTOMap, deptId);
                if (permission != null) {
                    deptPrivilegeDTO.setPermission(permission);
                }
            }
        }
    }

    /**
     * 递归查找父部门的权限
     *
     * @param departmentInfoMap
     * @param deptPrivilegeDTOMap
     * @param deptId
     * @return
     */
    private Integer findNonEmptyPermission(Map<Long, DepartmentInfo> departmentInfoMap, Map<Long, DeptPrivilegeDTO> deptPrivilegeDTOMap, Long deptId) {
        DeptPrivilegeDTO currentDTO = deptPrivilegeDTOMap.get(deptId);
        if (currentDTO == null) {
            return null;
        }

        // 检查当前部门的权限
        if (currentDTO.getPermission() != null) {
            return currentDTO.getPermission();
        }

        // 获取父部门ID
        DepartmentInfo departmentInfo = departmentInfoMap.get(deptId);
        if (departmentInfo == null || departmentInfo.getParentId() == null) {
            return null;
        }

        // 递归查找父部门的权限
        return findNonEmptyPermission(departmentInfoMap, deptPrivilegeDTOMap, departmentInfo.getParentId());
    }

    /**
     * 构建部门权限树结构
     *
     * @param deptPrivilegeDTOMap
     * @param departmentInfoMap
     * @return
     */
    private ArrayList<DeptPrivilegeDTO> buildTree(Map<Long, DeptPrivilegeDTO> deptPrivilegeDTOMap, Map<Long, DepartmentInfo> departmentInfoMap) {
        ArrayList<DeptPrivilegeDTO> tree = Lists.newArrayList();

        for (Map.Entry<Long, DeptPrivilegeDTO> dtoEntry : deptPrivilegeDTOMap.entrySet()) {
            DepartmentInfo departmentInfo = departmentInfoMap.get(dtoEntry.getKey());
            DeptPrivilegeDTO parentDeptPrivilegeDTO = deptPrivilegeDTOMap.get(departmentInfo.getParentId());
            if (Objects.isNull(parentDeptPrivilegeDTO))
                // 如果部门没有父部门，则将其添加到根节点列表中
                tree.add(dtoEntry.getValue());
            else {
                // 将当前部门添加到父部门的子部门列表中
                if (CollUtil.isEmpty(parentDeptPrivilegeDTO.getSubDeptPrivilegeList()))
                    parentDeptPrivilegeDTO.setSubDeptPrivilegeList(Lists.newArrayList());
                parentDeptPrivilegeDTO.getSubDeptPrivilegeList().add(dtoEntry.getValue());
            }
        }
        return tree;
    }


    @Override
    @Transactional
    public Boolean transferProperty(List<TransferPropertyReq> reqs) throws Exception {
        for (TransferPropertyReq req : reqs) {
            transfer(req);
        }
        return true;
    }

    protected void transfer(TransferPropertyReq req) throws Exception {
        if (req.getTransferType().equals(TransferTypeEnums.DELETE)) {
            //delete
            for (PrivilegeTypeEnums value : PrivilegeTypeEnums.values()) {
                userPrivilegeDomainService.deleteByUserId(value.getCode(), List.of(Long.valueOf(UserContext.getUser().getUserId())));
            }
        } else {
            //transfer
            Map<String, Object> params = Maps.newHashMap();
            Optional<TransferPropertyReq.TransferPropertyElement> sameUser = req.getTransferProperties().stream().filter(p -> p.getUserId().equals(p.getTargetUserId())).findAny();
            if (sameUser.isPresent()) {
                throw new ApplicationException(ErrCodeEnum.TRANSFER_PROPERTY_SAME_USER);
            }
            //判断助手中要不要删除知识库信息

            if (CollUtil.isNotEmpty(req.getTransferProperties())) {
                for (TransferPropertyReq.TransferPropertyElement transferProperty : req.getTransferProperties()) {
                    params.put("userId", transferProperty.getUserId());
                    UserPrivilege userPrivilege = UserPrivilege.builder().userId(transferProperty.getTargetUserId()).build();
                    params.put("bizType", transferProperty.getType().getCode());
                    UserInfo userInfo = userInfoDomainService.getUserInfoById(transferProperty.getUserId());
                    UserInfo targetUserInfo = userInfoDomainService.getUserInfoById(transferProperty.getTargetUserId());
                    userPrivilegeDomainService.updateByMap(userPrivilege, params);

                    switch (transferProperty.getType()) {
                        case KNOWLEDGE_BASE:
                            indexClient.transferKbProperty(userInfo.getUserName(), targetUserInfo.getUserName());
                            break;
                        case MODEL:
                            indexClient.transferModelProperty(userInfo.getUserName(), targetUserInfo.getUserName());
                            break;
                        case INDEX_CONF:
                            searchConfigClient.transferSearchConfigProperty(userInfo.getUserName(), targetUserInfo.getUserName());
                            break;
                    }
                }
            }
        }
    }


    @Override
    public List<PrivilegeTypeEnums> getTransferType(Long userId) {
        userId = Objects.nonNull(userId) ? userId : Long.valueOf(UserContext.getUser().getUserId());
        UserInfo userInfo = userInfoDomainService.getUserInfoById(userId);
        return userPrivilegeDomainService.getTransferType(userId, userInfo.getUserName());
    }
}
