package com.gientech.ragauthservice.domain.mapper;

import com.gientech.ragauthservice.domain.entity.GroupInfo;
import com.gientech.ragauthservice.domain.model.GroupInfoDO;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.MapKey;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;
import java.util.Map;

/**
 * <p>
 * 机构组 Mapper 接口
 * </p>
 *
 * @author wudf
 * @since 2024-07-23
 */
@Mapper
public interface GroupInfoMapper extends BaseMapper<GroupInfoDO> {

    @MapKey("id")
    Map<Long, GroupInfoDO> findByIds(@Param("ids") List<Long> groupIds);
}
