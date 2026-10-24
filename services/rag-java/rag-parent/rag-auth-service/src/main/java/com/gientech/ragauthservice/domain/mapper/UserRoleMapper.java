package com.gientech.ragauthservice.domain.mapper;

import com.gientech.ragauthservice.domain.model.UserRoleDO;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * <p>
 * 用户-角色关系表 Mapper 接口
 * </p>
 *
 * @author wudf
 * @since 2024-06-26
 */
@Mapper
public interface UserRoleMapper extends BaseMapper<UserRoleDO> {

    void saveBatch(@Param("list") List<UserRoleDO> userRoleDOS);
}
