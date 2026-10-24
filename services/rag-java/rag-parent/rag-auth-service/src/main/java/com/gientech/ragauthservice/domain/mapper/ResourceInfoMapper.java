package com.gientech.ragauthservice.domain.mapper;

import com.gientech.ragauthservice.domain.model.ResourceInfoDO;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.gientech.ragauthservice.domain.model.ResourceInfoWithVisibleDO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * <p>
 * 资源表 Mapper 接口
 * </p>
 *
 * @author wudf
 * @since 2024-06-26
 */
@Mapper
public interface ResourceInfoMapper extends BaseMapper<ResourceInfoDO> {

    List<ResourceInfoDO> queryByRoleIds(@Param("roleIds") List<Long> roleIds);

    List<ResourceInfoWithVisibleDO> queryVisibleByRoleIds(@Param("roleIds") List<Long> roleIds);
}
