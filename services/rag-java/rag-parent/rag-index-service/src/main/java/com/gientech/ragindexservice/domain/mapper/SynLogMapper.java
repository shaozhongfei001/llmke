package com.gientech.ragindexservice.domain.mapper;

import com.gientech.ragindexservice.domain.model.SynLogDO;
import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import org.apache.ibatis.annotations.MapKey;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;
import java.util.Map;

/**
 * <p>
 * 日志 Mapper 接口
 * </p>
 *
 * @author wudf
 * @since 2024-08-27
 */
@Mapper
public interface SynLogMapper extends BaseMapper<SynLogDO> {

    @MapKey("targetId")
    Map<Long, SynLogDO> findByFileIds(@Param("fileIds") List<Long> fileIds);
}
