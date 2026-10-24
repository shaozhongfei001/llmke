package com.gientech.ragauthservice.domain.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.gientech.ragauthservice.domain.model.UserPrivilegeDO;
import com.gientech.ragcommon.auth.dto.PrivilegeDTO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * <p>
 * 用户-数据权限关联 Mapper 接口
 * </p>
 *
 * @author wudf
 * @since 2024-07-31
 */
@Mapper
public interface UserPrivilegeMapper extends BaseMapper<UserPrivilegeDO> {

    void saveBatch(List<UserPrivilegeDO> userPrivilegeDOS);

    List<PrivilegeDTO> getPermission(@Param("userId") Long userId, @Param("bizType") Integer bizType, @Param("targetId") Long targetId);

    int updatePermissionBatch(@Param("ids") List<Long> ids, @Param("permission") Integer permission, @Param("elementId") Long elementId);

    List<Integer> getTransferType(@Param("userId") Long userId, @Param("userName") String userName);
}
