package com.gientech.ragauthservice.domain.mapper;

import com.gientech.ragauthservice.domain.model.RoleResourceDO;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * <p>
 * 角色-资源关系表 Mapper 接口
 * </p>
 *
 * @author wudf
 * @since 2024-06-27
 */
@Mapper
public interface RoleResourceMapper extends BaseMapper<RoleResourceDO> {

    void saveBatch(@Param("list") List<RoleResourceDO> roleResourceDOS);
}
