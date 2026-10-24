package com.gientech.tools.database.domain.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.gientech.tools.database.domain.model.TLDatabaseDO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

/**
 * 数据库配置;
 * @Author ： xiaomin.zuo@gientech.com
 * @date : 2025-7-11
 */
@Mapper
public interface TLDatabaseMapper extends BaseMapper<TLDatabaseDO>  {
    Integer getHighestPermission(@Param("databaseId") Long databaseId, @Param("deptId") Long deptId, @Param("userId") Long userId, @Param("userName") String userName);
}
