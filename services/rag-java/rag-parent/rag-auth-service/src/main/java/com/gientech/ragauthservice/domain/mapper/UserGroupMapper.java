package com.gientech.ragauthservice.domain.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.gientech.ragauthservice.domain.entity.DepartmentInfo;
import com.gientech.ragauthservice.domain.entity.UserGroup;
import com.gientech.ragauthservice.domain.entity.UserInfo;
import com.gientech.ragauthservice.domain.model.UserGroupDO;
import com.gientech.ragauthservice.domain.model.UserInfoDO;
import org.apache.ibatis.annotations.MapKey;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;
import java.util.Map;

/**
 * <p>
 * 机构-用户关联表 Mapper 接口
 * </p>
 *
 * @author wudf
 * @since 2024-07-23
 */
@Mapper
public interface UserGroupMapper extends BaseMapper<UserGroupDO> {

    void saveBatch(@Param("list") List<UserGroupDO> copyToList);

    @MapKey("groupId")
    Map<Long, UserGroup> findByGroupIds(@Param("groupIds") List<Long> groupIds);

    List<UserInfo> getUserListByGroupList(@Param("groupIds") List<Long> groupIds);

    List<DepartmentInfo> getDeptListByGroupId(@Param("groupId") Long groupId);

    Page<UserInfoDO> flatUserList(@Param("groupId") Long groupId, Page<UserInfoDO> page);
}
