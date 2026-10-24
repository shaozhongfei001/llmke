package com.gientech.ragauthservice.domain.service;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragauthservice.domain.entity.DepartmentInfo;
import com.gientech.ragauthservice.domain.entity.UserGroup;
import com.gientech.ragauthservice.domain.entity.UserInfo;
import com.gientech.ragcommon.auth.dto.FrameElement;

import java.util.List;
import java.util.Map;

/**
 * <p>
 * 机构-用户关联表 服务类
 * </p>
 *
 * @author wudf
 * @since 2024-07-23
 */
public interface UserGroupDomainService {

    List<UserGroup> findByGroupId(Long groupId);

    void addUsers(Long groupId, List<Long> addUserIds);

    void delUsers(Long groupId, List<Long> delUserIds);

    Page<UserGroup> groupUserList(Long groupId, Long pageNo, Long pageSize);

    Page<UserInfo> flatUserList(Long groupId, Long pageNo, Long pageSize);

    Long userCount(Long groupId);

    Map<Long, UserGroup> findByIds(List<Long> groupIds);

    List<Long> listGroupIdsByUserId(Long userId);

    List<UserInfo> getUserListByGroupList(List<Long> groupIds);

    List<DepartmentInfo> getDepartmentListByGroupId(Long deptId);

    void addDepartments(Long groupId, List<Long> addDeptIds);

    void delDepartments(Long groupId, List<Long> delDeptIds);

    List<Long> listGroupIdsByDeptId(Long deptId);

    Long groupUserCount(Long groupId);
}
