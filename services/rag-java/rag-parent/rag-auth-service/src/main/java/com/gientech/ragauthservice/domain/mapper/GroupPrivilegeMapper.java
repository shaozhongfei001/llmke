package com.gientech.ragauthservice.domain.mapper;

import com.gientech.ragauthservice.domain.model.GroupPrivilegeDO;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * <p>
 * 机构组-数据权限关联 Mapper 接口
 * </p>
 *
 * @author wudf
 * @since 2024-07-31
 */
@Mapper
public interface GroupPrivilegeMapper extends BaseMapper<GroupPrivilegeDO> {

    void saveBatch(List<GroupPrivilegeDO> groupPrivilegeDOS);

    int updatePermissionBatch(@Param("ids") List<Long> ids, @Param("permission") Integer permission, @Param("elementId") Long elementId);
}
