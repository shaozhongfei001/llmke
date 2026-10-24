package com.gientech.ragauthservice.domain.repository;

import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragauthservice.domain.entity.DepartmentInfo;
import com.gientech.ragauthservice.domain.entity.UserGroup;
import com.gientech.ragauthservice.domain.entity.UserInfo;
import com.gientech.ragauthservice.domain.model.UserInfoDO;

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
public interface UserGroupRepository {

    List<UserGroup> findByGroupId(Long groupId);

    void delUser(Long groupId, List<Long> delUserIds);

    void saveUsers(Long groupId, List<Long> addUserIds);

    Page<UserGroup> groupUserList(Long groupId, Long pageNo, Long pageSize);

    Long userCount(Long groupId);

    Map<Long, UserGroup> findByGroupIds(List<Long> groupIds);

    List<Long> listGroupIdsByUserId(Long userId);

    List<UserInfo> getUserListByGroupList(List<Long> groupIds);

    List<DepartmentInfo> getDeptListByGroupId(Long groupId);

    Page<UserInfoDO> flatUserList(Long groupId, Long pageNo, Long pageSize);

    void saveDepartments(Long groupId, List<Long> addDeptIds);

    void delDepartments(Long groupId, List<Long> delDeptIds);

    List<Long> listGroupIdsByDeptId(Long deptId);

    Long groupUserCount(Long id);
}
